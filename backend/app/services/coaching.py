"""Behavioral nudge and coaching engine.

Generates motivational and actionable Discord messages based on spending patterns,
streaks, milestones, and anomalies.
"""

import random
from datetime import date, timedelta
from ollama import AsyncClient

from app.config import settings
from app.services.discord_alerts import send_discord_alert


async def generate_daily_nudge(
    health_score: int,
    net_monthly: float,
    days_on_budget: int,
    total_debt: float,
    debt_change_7d: float,
    top_waste_category: str | None = None,
) -> str:
    """Generate a coaching nudge using local LLM."""
    context = f"""Financial snapshot:
- Health Score: {health_score}/100
- Net monthly (income - expenses): ${net_monthly:.2f}
- Days staying within budget this month: {days_on_budget}
- Total debt: ${total_debt:.2f}
- Debt change (7 days): ${debt_change_7d:+.2f}
- Top waste category: {top_waste_category or 'none detected'}"""

    prompt = f"""You are a supportive but direct financial coach helping someone get out of debt.
Based on this snapshot, write a SHORT motivational Discord message (2-3 sentences max).

{context}

Rules:
- Be encouraging but honest
- Include one specific actionable tip
- If they're making progress, celebrate it
- If debt went up, address it directly but kindly
- Keep it under 200 characters if possible
- Use a casual, friendly tone

Message:"""

    try:
        client = AsyncClient(host=settings.ollama_base_url)
        response = await client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},
        )
        return response["message"]["content"].strip()
    except Exception:
        return _fallback_nudge(health_score, net_monthly, days_on_budget, debt_change_7d)


def _fallback_nudge(score: int, net: float, streak: int, debt_change: float) -> str:
    """Rule-based fallback when LLM is unavailable."""
    messages = []

    if debt_change < -50:
        messages.append(f"Debt down ${abs(debt_change):.0f} this week! Keep that momentum going.")
    elif debt_change > 50:
        messages.append(f"Debt crept up ${debt_change:.0f} this week. Let's find one thing to cut today.")

    if streak >= 7:
        messages.append(f"{streak}-day budget streak! You're building real discipline.")
    elif streak >= 3:
        messages.append(f"{streak} days on budget. Keep going for the full week!")

    if net > 0:
        messages.append(f"${net:.0f} surplus this month — direct it to your highest-interest debt.")
    elif net < 0:
        messages.append(f"Running ${abs(net):.0f} over budget. Review this week's discretionary spending.")

    if score >= 80:
        messages.append("Your financial health is strong. Stay the course!")
    elif score < 50:
        messages.append("Score needs work, but every small step counts. Focus on one win today.")

    return random.choice(messages) if messages else "Stay focused on your debt-free goal. Every dollar counts!"


# ── Milestone & Anomaly Alerts ──

async def check_milestones_and_alert(
    total_debt: float,
    prev_debt: float,
    health_score: int,
    monthly_savings: float,
):
    """Check for celebration-worthy milestones and send Discord alerts."""
    alerts = []

    # Debt milestones (every $1000 paid off)
    prev_thousands = int(prev_debt / 1000)
    curr_thousands = int(total_debt / 1000)
    if curr_thousands < prev_thousands:
        paid_off = (prev_thousands - curr_thousands) * 1000
        alerts.append(f"**MILESTONE** You've paid off another ${paid_off:,}! Total debt now: ${total_debt:,.2f}")

    # Health score improvements
    if health_score >= 90 and health_score > 85:
        alerts.append(f"**Health Score: {health_score}/100** — You're in excellent financial shape!")

    # Positive savings streak
    if monthly_savings > 500:
        alerts.append(f"**Strong month!** ${monthly_savings:,.2f} saved. Consider a lump-sum debt payment.")

    for alert in alerts:
        await send_discord_alert(alert)

    return alerts


async def detect_anomaly_and_alert(
    category: str,
    current_month_total: float,
    avg_3month: float,
    months_to_debt_free_impact: float = 0,
):
    """Detect spending anomalies and send proactive warnings."""
    if avg_3month <= 0:
        return None

    pct_over = (current_month_total - avg_3month) / avg_3month * 100

    if pct_over > 25:
        msg = (
            f"**Pattern Alert: {category}** spending up {pct_over:.0f}% vs 3-month average "
            f"(${current_month_total:.2f} vs ${avg_3month:.2f})"
        )
        if months_to_debt_free_impact > 0:
            msg += f"\nAt this rate: +{months_to_debt_free_impact:.1f} months to debt freedom."
        msg += "\nCut back now to stay on track!"
        await send_discord_alert(msg)
        return msg

    return None
