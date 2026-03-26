"""System Overview route — the command center.

Combines debt burndown projection, spending trend analysis, budget adherence,
debt-free date calculation, and overspending impact detection into one endpoint.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.debt import Debt
from app.models.income import Income
from app.models.budget import Budget
from app.routes.dashboard import monthly_income_amount, ESSENTIAL_CATEGORIES

router = APIRouter()


@router.get("/")
async def system_overview(db: AsyncSession = Depends(get_db)):
    """Full system overview: burndown, debt-free date, trends, alerts."""
    today = date.today()
    month_start = today.replace(day=1)

    # ── Gather core data ──
    incomes_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = incomes_result.scalars().all()
    monthly_income = sum(monthly_income_amount(i) for i in incomes)

    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min_payments = sum(float(d.minimum_payment) for d in debts)
    avg_rate = (sum(float(d.interest_rate) for d in debts) / len(debts)) if debts else 0

    # ── Monthly spending history (last 12 months) ──
    twelve_months_ago = today - timedelta(days=365)
    txn_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= twelve_months_ago,
            )
        )
    )
    all_expenses = txn_result.scalars().all()

    # Group expenses by month
    monthly_expenses: dict[str, float] = defaultdict(float)
    monthly_essential: dict[str, float] = defaultdict(float)
    monthly_discretionary: dict[str, float] = defaultdict(float)
    for t in all_expenses:
        month_key = t.date.strftime("%Y-%m")
        amount = float(t.amount)
        monthly_expenses[month_key] += amount
        if t.category in ESSENTIAL_CATEGORIES:
            monthly_essential[month_key] += amount
        else:
            monthly_discretionary[month_key] += amount

    # Current month expenses
    current_month_key = today.strftime("%Y-%m")
    current_expenses = monthly_expenses.get(current_month_key, 0)

    # Average monthly expenses (last 3 months for stability)
    sorted_months = sorted(monthly_expenses.keys(), reverse=True)
    recent_months = sorted_months[:3] if len(sorted_months) >= 3 else sorted_months
    avg_monthly_expenses = (
        sum(monthly_expenses[m] for m in recent_months) / len(recent_months)
        if recent_months else current_expenses
    )

    # ── Spending trend ──
    if len(sorted_months) >= 2:
        latest = monthly_expenses.get(sorted_months[0], 0)
        prev = monthly_expenses.get(sorted_months[1], 0)
        spending_trend_pct = ((latest - prev) / prev * 100) if prev > 0 else 0
    else:
        spending_trend_pct = 0

    if spending_trend_pct > 10:
        spending_trend = "rising"
    elif spending_trend_pct < -10:
        spending_trend = "falling"
    else:
        spending_trend = "stable"

    # ── Budget adherence ──
    budget_result = await db.execute(select(Budget).where(Budget.is_active == True))
    budgets = budget_result.scalars().all()

    # Sum current month spending by category
    current_month_by_cat: dict[str, float] = defaultdict(float)
    for t in all_expenses:
        if t.date.strftime("%Y-%m") == current_month_key:
            current_month_by_cat[t.category.value] += float(t.amount)

    budgets_over = 0
    budgets_total = len(budgets)
    budget_details = []
    for b in budgets:
        spent = current_month_by_cat.get(b.category.value, 0)
        limit = float(b.monthly_limit)
        pct = (spent / limit * 100) if limit > 0 else 0
        is_over = spent > limit
        if is_over:
            budgets_over += 1
        budget_details.append({
            "category": b.category.value,
            "spent": round(spent, 2),
            "limit": round(limit, 2),
            "pct": round(pct, 1),
            "over": is_over,
        })

    budget_adherence_pct = (
        ((budgets_total - budgets_over) / budgets_total * 100)
        if budgets_total > 0 else 100
    )

    # ── Debt-free date calculation (3 scenarios) ──
    available_for_debt = max(monthly_income - avg_monthly_expenses, total_min_payments)

    scenarios = {}
    for name, payment in [
        ("on_budget", available_for_debt),
        ("minimum_only", total_min_payments),
        ("aggressive", available_for_debt * 1.15),  # 15% more aggressive
    ]:
        months, interest = _simulate_payoff(total_debt, payment, avg_rate)
        target_date = today + relativedelta(months=months) if months < 600 else None
        scenarios[name] = {
            "months": months,
            "total_interest": round(interest, 2),
            "debt_free_date": target_date.isoformat() if target_date else "Never at this rate",
            "monthly_payment": round(payment, 2),
        }

    # ── Burndown chart data (month-by-month projection) ──
    burndown = _generate_burndown(
        debts=debts,
        monthly_payment=available_for_debt,
        months_to_project=max(scenarios["on_budget"]["months"] + 3, 12),
    )

    # ── Overspending impact detection ──
    alerts = []

    # Compare current month to budget plan
    if current_expenses > avg_monthly_expenses * 1.1:
        overspend_amount = current_expenses - avg_monthly_expenses
        # Recalculate with overspending
        reduced_debt_payment = max(monthly_income - current_expenses, total_min_payments)
        overspend_months, _ = _simulate_payoff(total_debt, reduced_debt_payment, avg_rate)
        original_months = scenarios["on_budget"]["months"]
        months_added = overspend_months - original_months

        if months_added > 0:
            alerts.append({
                "type": "overspending",
                "severity": "high" if months_added >= 3 else "medium" if months_added >= 1 else "low",
                "title": f"Overspending detected: +${overspend_amount:,.0f} this month",
                "message": (
                    f"You're spending ${overspend_amount:,.0f} more than your 3-month average. "
                    f"If this continues, your debt-free date shifts from "
                    f"{scenarios['on_budget']['debt_free_date']} to "
                    f"{(today + relativedelta(months=overspend_months)).isoformat()} "
                    f"(+{months_added} months)."
                ),
                "months_impact": months_added,
                "amount_over": round(overspend_amount, 2),
            })

    # Budget breaches
    for bd in budget_details:
        if bd["over"]:
            over_amount = bd["spent"] - bd["limit"]
            alerts.append({
                "type": "budget_breach",
                "severity": "high" if bd["pct"] > 150 else "medium",
                "title": f"{bd['category']} over budget",
                "message": f"${bd['spent']:,.2f} spent vs ${bd['limit']:,.2f} limit ({bd['pct']:.0f}%)",
                "amount_over": round(over_amount, 2),
            })

    # Spending trend warning
    if spending_trend == "rising" and spending_trend_pct > 15:
        alerts.append({
            "type": "trend_warning",
            "severity": "medium",
            "title": f"Spending trending up {spending_trend_pct:.0f}%",
            "message": "Month-over-month spending is increasing. Review discretionary categories.",
        })

    # Positive reinforcement
    if spending_trend == "falling" and spending_trend_pct < -10:
        alerts.append({
            "type": "positive",
            "severity": "good",
            "title": f"Spending down {abs(spending_trend_pct):.0f}%!",
            "message": "Great progress — you're spending less than last month. Keep it up!",
        })

    # ── Monthly spending history for charts ──
    spending_history = []
    for i in range(11, -1, -1):
        m = (today - relativedelta(months=i)).strftime("%Y-%m")
        spending_history.append({
            "month": m,
            "total": round(monthly_expenses.get(m, 0), 2),
            "essential": round(monthly_essential.get(m, 0), 2),
            "discretionary": round(monthly_discretionary.get(m, 0), 2),
        })

    return {
        # Summary stats
        "total_debt": round(total_debt, 2),
        "monthly_income": round(monthly_income, 2),
        "avg_monthly_expenses": round(avg_monthly_expenses, 2),
        "current_month_expenses": round(current_expenses, 2),
        "net_available_for_debt": round(available_for_debt, 2),
        "spending_trend": spending_trend,
        "spending_trend_pct": round(spending_trend_pct, 1),
        "budget_adherence_pct": round(budget_adherence_pct, 1),

        # Debt-free projections
        "debt_free_scenarios": scenarios,

        # Burndown chart
        "burndown": burndown,

        # Spending history
        "spending_history": spending_history,

        # Budget details
        "budget_status": budget_details,

        # Alerts & warnings
        "alerts": alerts,

        # Per-debt breakdown
        "debts": [
            {
                "name": d.name,
                "balance": round(float(d.current_balance), 2),
                "rate": float(d.interest_rate),
                "min_payment": round(float(d.minimum_payment), 2),
            }
            for d in debts
        ],
    }


def _simulate_payoff(balance: float, monthly_payment: float, annual_rate: float) -> tuple[int, float]:
    """Simulate debt payoff. Returns (months, total_interest)."""
    monthly_rate = annual_rate / 100 / 12
    months = 0
    total_interest = 0.0
    remaining = balance

    while remaining > 0.01 and months < 600:
        interest = remaining * monthly_rate
        total_interest += interest
        remaining = remaining + interest - monthly_payment
        months += 1
        if monthly_payment <= interest and months > 1:
            return 999, total_interest  # Never pays off

    return months, total_interest


def _generate_burndown(debts: list[Debt], monthly_payment: float, months_to_project: int) -> list[dict]:
    """Generate month-by-month debt burndown projection."""
    if not debts:
        return []

    total_balance = sum(float(d.current_balance) for d in debts)
    avg_rate = sum(float(d.interest_rate) for d in debts) / len(debts)
    monthly_rate = avg_rate / 100 / 12

    today = date.today()
    data = []
    remaining = total_balance

    # Cap projection to avoid huge arrays
    months_to_project = min(months_to_project, 120)

    for i in range(months_to_project + 1):
        month_date = today + relativedelta(months=i)
        data.append({
            "month": month_date.strftime("%Y-%m"),
            "balance": round(max(remaining, 0), 2),
            "interest": round(remaining * monthly_rate, 2) if remaining > 0 else 0,
            "payment": round(min(monthly_payment, remaining + remaining * monthly_rate), 2) if remaining > 0 else 0,
        })

        if remaining <= 0:
            break

        interest = remaining * monthly_rate
        remaining = remaining + interest - monthly_payment

    return data
