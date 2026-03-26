"""Detects recurring subscriptions and scores them for waste potential.

Enhanced with LLM-powered cancel/keep/negotiate recommendations.
"""

from collections import defaultdict
from datetime import date, timedelta
from dataclasses import dataclass
import json
import re

from ollama import AsyncClient

from app.config import settings
from app.models.transaction import Transaction, TransactionCategory


@dataclass
class Subscription:
    merchant: str
    category: str
    avg_amount: float
    frequency_days: int
    occurrence_count: int
    last_charged: date
    total_spent: float
    waste_score: int = 0  # 0-100, set by LLM or rules
    suggestion: str = ""
    action: str = ""  # "cancel", "downgrade", "negotiate", "keep"
    cancel_difficulty: str = ""  # "easy", "medium", "hard"
    cancel_method: str = ""  # how to cancel
    annual_cost: float = 0
    alternatives: str = ""  # free/cheaper alternatives


KNOWN_SUBSCRIPTIONS = {
    "netflix": {"cancel": "easy", "method": "Netflix.com → Account → Cancel Membership", "alt": "Free: Tubi, Pluto TV, YouTube"},
    "spotify": {"cancel": "easy", "method": "Spotify.com → Account → Subscription → Cancel", "alt": "Free Spotify tier, YouTube Music free"},
    "hulu": {"cancel": "easy", "method": "Hulu.com → Account → Cancel", "alt": "Free: Tubi, Pluto TV, Peacock free tier"},
    "disney+": {"cancel": "easy", "method": "DisneyPlus.com → Account → Subscription → Cancel", "alt": "Bundle with Hulu to save"},
    "youtube premium": {"cancel": "easy", "method": "YouTube → Settings → Memberships → Cancel", "alt": "Use uBlock Origin for ad-free (desktop)"},
    "amazon prime": {"cancel": "medium", "method": "Amazon → Account → Prime → End Membership", "alt": "Cancel and buy items over $35 for free shipping"},
    "apple music": {"cancel": "easy", "method": "Settings → Apple ID → Subscriptions → Cancel", "alt": "Free Spotify tier, YouTube Music free"},
    "apple tv": {"cancel": "easy", "method": "Settings → Apple ID → Subscriptions → Cancel", "alt": "Free: Tubi, Pluto TV"},
    "hbo max": {"cancel": "easy", "method": "HBOMax.com → Settings → Subscription → Cancel", "alt": "Rotate: subscribe 1 month, binge, cancel"},
    "paramount+": {"cancel": "easy", "method": "ParamountPlus.com → Account → Cancel", "alt": "Free: Pluto TV (same parent company)"},
    "peacock": {"cancel": "easy", "method": "PeacockTV.com → Account → Cancel", "alt": "Peacock has a free tier with ads"},
    "crunchyroll": {"cancel": "easy", "method": "Crunchyroll.com → Settings → Cancel", "alt": "Free tier with ads available"},
    "adobe": {"cancel": "hard", "method": "Adobe.com → Account → Plans → Cancel (early termination fee!)", "alt": "GIMP (free), Affinity (one-time $70), Canva"},
    "microsoft 365": {"cancel": "medium", "method": "Microsoft.com → Services → Cancel", "alt": "LibreOffice (free), Google Docs (free)"},
    "dropbox": {"cancel": "medium", "method": "Dropbox.com → Settings → Plan → Cancel", "alt": "Google Drive 15GB free, iCloud"},
    "google one": {"cancel": "easy", "method": "one.google.com → Settings → Cancel", "alt": "Free 15GB, clean up old files"},
    "nordvpn": {"cancel": "medium", "method": "NordVPN.com → Dashboard → Cancel", "alt": "ProtonVPN free tier, Windscribe free"},
    "expressvpn": {"cancel": "medium", "method": "ExpressVPN.com → Subscription → Cancel", "alt": "ProtonVPN free tier"},
    "gym": {"cancel": "hard", "method": "Visit in person or send certified letter (check contract)", "alt": "Home workouts: YouTube, Nike Training Club (free)"},
    "planet fitness": {"cancel": "hard", "method": "Must cancel IN PERSON at home club or via certified mail", "alt": "Home workouts, outdoor running"},
    "anytime fitness": {"cancel": "hard", "method": "30-day written notice required at home club", "alt": "Home workouts, outdoor exercise"},
    "peloton": {"cancel": "medium", "method": "Peloton app → Profile → Membership → Cancel", "alt": "YouTube fitness, Nike Training Club (free)"},
    "audible": {"cancel": "easy", "method": "Audible.com → Account → Cancel (keep credits!)", "alt": "Libby app (free with library card)"},
    "kindle unlimited": {"cancel": "easy", "method": "Amazon → Memberships → Kindle Unlimited → Cancel", "alt": "Libby app (free with library card)"},
    "xbox game pass": {"cancel": "easy", "method": "Microsoft.com → Services → Game Pass → Cancel", "alt": "Buy used games, free-to-play titles"},
    "playstation plus": {"cancel": "easy", "method": "PS console → Settings → Account → Subscriptions", "alt": "Free-to-play games, buy used"},
    "doordash dashpass": {"cancel": "easy", "method": "DoorDash app → Account → DashPass → Cancel", "alt": "Cook at home, meal prep Sundays"},
    "uber one": {"cancel": "easy", "method": "Uber app → Account → Uber One → Cancel", "alt": "Compare per-order: often cheaper without membership"},
    "grubhub+": {"cancel": "easy", "method": "Grubhub → Account → Membership → Cancel", "alt": "Pick up instead of delivery to save fees"},
    "instacart": {"cancel": "easy", "method": "Instacart.com → Account → Instacart+ → Cancel", "alt": "Shop in person to save markups + fees"},
}


def detect_subscriptions(transactions: list[Transaction], lookback_days: int = 90) -> list[Subscription]:
    """Analyze transactions to find recurring subscriptions."""
    cutoff = date.today() - timedelta(days=lookback_days)
    recent = [t for t in transactions if t.date >= cutoff and t.transaction_type.value == "expense"]

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for txn in recent:
        key = _normalize_merchant(txn.merchant or txn.description)
        if key:
            by_merchant[key].append(txn)

    subscriptions = []
    for merchant, txns in by_merchant.items():
        if len(txns) < 2:
            continue

        amounts = [float(t.amount) for t in txns]
        avg = sum(amounts) / len(amounts)
        variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)

        if variance > (avg * 0.3) ** 2 and not _is_known_sub(merchant):
            continue

        dates = sorted([t.date for t in txns])
        if len(dates) >= 2:
            gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_gap = sum(gaps) / len(gaps)
        else:
            avg_gap = 30

        waste_score = _score_waste(merchant, txns[0].category, avg, avg_gap)
        known_info = _get_known_info(merchant)
        annual = avg * (365 / max(avg_gap, 1))

        sub = Subscription(
            merchant=merchant,
            category=txns[0].category.value,
            avg_amount=round(avg, 2),
            frequency_days=round(avg_gap),
            occurrence_count=len(txns),
            last_charged=max(t.date for t in txns),
            total_spent=round(sum(amounts), 2),
            waste_score=waste_score,
            suggestion=_suggest_action(merchant, waste_score, avg),
            action=_determine_action(waste_score),
            cancel_difficulty=known_info.get("cancel", "unknown"),
            cancel_method=known_info.get("method", "Check the service's website → Account → Cancel/Subscription"),
            annual_cost=round(annual, 2),
            alternatives=known_info.get("alt", ""),
        )
        subscriptions.append(sub)

    return sorted(subscriptions, key=lambda s: s.waste_score, reverse=True)


async def get_llm_subscription_analysis(subs: list[Subscription], monthly_income: float, total_debt: float) -> dict:
    """Get LLM-powered deep analysis with personalized cancel/keep recommendations."""
    if not subs:
        return {"recommendations": [], "total_saveable": 0, "summary": "No subscriptions detected."}

    sub_text = "\n".join(
        f"- {s.merchant}: ${s.avg_amount:.2f}/mo (every ~{s.frequency_days} days), "
        f"category: {s.category}, total spent: ${s.total_spent:.2f}"
        for s in subs
    )

    prompt = f"""You are a debt-elimination financial advisor. Analyze these recurring subscriptions for someone trying to get out of debt.

Monthly income: ${monthly_income:.2f}
Total debt: ${total_debt:.2f}

Active subscriptions:
{sub_text}

For EACH subscription, provide:
1. action: "cancel", "downgrade", "negotiate", or "keep"
2. reason: one sentence explanation
3. savings_if_cancelled: monthly dollar amount saved
4. priority: 1 (cancel immediately) to 5 (probably keep)
5. negotiation_script: if action is "negotiate", provide a brief phone script

Also provide:
- total_monthly_savings: sum of all recommended cancellations/downgrades
- debt_freedom_impact: how many months sooner they'd be debt-free with the savings
- one_sentence_summary: motivational summary

Return ONLY valid JSON. Example format:
{{
  "recommendations": [
    {{"merchant": "Netflix", "action": "cancel", "reason": "Multiple streaming services detected", "savings_if_cancelled": 15.99, "priority": 2, "negotiation_script": ""}}
  ],
  "total_monthly_savings": 45.99,
  "debt_freedom_impact_months": 3,
  "summary": "Cutting 3 subscriptions saves $46/mo..."
}}

JSON:"""

    try:
        client = AsyncClient(host=settings.ollama_base_url)
        response = await client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
        content = response["message"]["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    # Fallback
    total_saveable = sum(s.avg_amount for s in subs if s.waste_score >= 60)
    return {
        "recommendations": [
            {"merchant": s.merchant, "action": s.action, "reason": s.suggestion,
             "savings_if_cancelled": s.avg_amount, "priority": 1 if s.waste_score >= 70 else 3}
            for s in subs if s.waste_score >= 50
        ],
        "total_monthly_savings": round(total_saveable, 2),
        "debt_freedom_impact_months": 0,
        "summary": f"${total_saveable:.2f}/mo in potential subscription savings detected.",
    }


def _normalize_merchant(name: str) -> str:
    return name.strip().lower().split(" - ")[0].split("*")[0].strip()


def _is_known_sub(merchant: str) -> bool:
    merchant_lower = merchant.lower()
    return any(sub in merchant_lower for sub in KNOWN_SUBSCRIPTIONS)


def _get_known_info(merchant: str) -> dict:
    merchant_lower = merchant.lower()
    for key, info in KNOWN_SUBSCRIPTIONS.items():
        if key in merchant_lower:
            return info
    return {}


def _determine_action(waste_score: int) -> str:
    if waste_score >= 70:
        return "cancel"
    elif waste_score >= 55:
        return "downgrade"
    elif waste_score >= 40:
        return "negotiate"
    return "keep"


def _score_waste(merchant: str, category: TransactionCategory, amount: float, freq_days: float) -> int:
    score = 30
    high_waste_cats = {
        TransactionCategory.ENTERTAINMENT: 20,
        TransactionCategory.SUBSCRIPTIONS: 15,
        TransactionCategory.DINING: 25,
        TransactionCategory.SHOPPING: 20,
    }
    score += high_waste_cats.get(category, 0)
    if _is_known_sub(merchant):
        score += 10
    if amount > 30:
        score += 15
    elif amount > 15:
        score += 5
    if freq_days < 10:
        score += 10
    return min(score, 100)


def _suggest_action(merchant: str, waste_score: int, amount: float) -> str:
    known = _get_known_info(merchant)
    alt = known.get("alt", "")

    if waste_score >= 70:
        base = f"Cancel {merchant} to save ${amount:.2f}/mo."
        if alt:
            base += f" Try instead: {alt}"
        return base
    elif waste_score >= 50:
        return f"Review {merchant} usage. Downgrade or share account to reduce costs."
    elif waste_score >= 30:
        return f"Monitor {merchant}. Consider if ${amount:.2f}/mo aligns with your debt-free goal."
    return f"{merchant} appears to be a reasonable expense."
