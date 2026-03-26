"""Financial Health Score Engine.

Computes a 0-100 composite score from multiple financial health indicators.
"""

from dataclasses import dataclass


@dataclass
class HealthScoreBreakdown:
    overall_score: int  # 0-100
    grade: str  # A, B, C, D, F
    components: dict[str, dict]  # name -> {score, weight, detail}
    tips: list[str]
    trend: str  # "improving", "declining", "stable"


def calculate_health_score(
    monthly_income: float,
    monthly_expenses: float,
    total_debt: float,
    total_minimum_payments: float,
    essential_expenses: float,
    discretionary_expenses: float,
    emergency_fund: float = 0,
    on_time_payments_pct: float = 100,
    budget_adherence_pct: float = 100,
    debt_change_30d: float = 0,  # negative = paying down
) -> HealthScoreBreakdown:
    """Calculate a comprehensive financial health score."""
    components = {}
    tips = []

    # 1. Savings Rate (25% weight)
    if monthly_income > 0:
        savings_rate = (monthly_income - monthly_expenses) / monthly_income * 100
        savings_score = min(max(savings_rate * 5, 0), 100)  # 20% savings = 100
    else:
        savings_rate = 0
        savings_score = 0

    components["savings_rate"] = {
        "score": round(savings_score),
        "weight": 0.25,
        "detail": f"{savings_rate:.1f}% of income saved",
    }
    if savings_rate < 10:
        tips.append("Aim to save at least 10-20% of income. Even $50/month helps.")

    # 2. Debt-to-Income Ratio (25% weight)
    if monthly_income > 0:
        dti = total_minimum_payments / monthly_income * 100
        dti_score = max(100 - dti * 2.5, 0)  # 0% DTI = 100, 40% DTI = 0
    else:
        dti = 100
        dti_score = 0

    components["debt_to_income"] = {
        "score": round(dti_score),
        "weight": 0.25,
        "detail": f"{dti:.1f}% DTI ratio",
    }
    if dti > 36:
        tips.append(f"DTI at {dti:.0f}% is high. Focus on paying down highest-interest debt first.")

    # 3. Essential Expense Ratio (15% weight)
    if monthly_expenses > 0:
        essential_ratio = essential_expenses / monthly_expenses * 100
        # 50-70% essential is healthy
        if essential_ratio <= 50:
            essential_score = 100
        elif essential_ratio <= 70:
            essential_score = 100 - (essential_ratio - 50) * 2
        else:
            essential_score = max(60 - (essential_ratio - 70) * 2, 0)
    else:
        essential_ratio = 0
        essential_score = 50

    components["expense_balance"] = {
        "score": round(essential_score),
        "weight": 0.15,
        "detail": f"{essential_ratio:.0f}% essential / {100-essential_ratio:.0f}% discretionary",
    }
    if discretionary_expenses > essential_expenses * 0.5:
        tips.append("Discretionary spending is high relative to essentials. Review subscriptions and dining.")

    # 4. Budget Adherence (15% weight)
    adherence_score = min(budget_adherence_pct, 100)
    components["budget_adherence"] = {
        "score": round(adherence_score),
        "weight": 0.15,
        "detail": f"{budget_adherence_pct:.0f}% within budget",
    }
    if budget_adherence_pct < 80:
        tips.append("You're exceeding budgets frequently. Consider adjusting limits to be realistic, then tighten.")

    # 5. Emergency Fund (10% weight)
    if monthly_expenses > 0:
        months_covered = emergency_fund / monthly_expenses
        ef_score = min(months_covered / 3 * 100, 100)  # 3 months = 100
    else:
        months_covered = 0
        ef_score = 0

    components["emergency_fund"] = {
        "score": round(ef_score),
        "weight": 0.10,
        "detail": f"{months_covered:.1f} months of expenses covered",
    }
    if months_covered < 1:
        tips.append("Build a $1,000 starter emergency fund before aggressive debt payoff.")

    # 6. Payment Reliability (10% weight)
    payment_score = min(on_time_payments_pct, 100)
    components["payment_reliability"] = {
        "score": round(payment_score),
        "weight": 0.10,
        "detail": f"{on_time_payments_pct:.0f}% on-time payments",
    }
    if on_time_payments_pct < 100:
        tips.append("Missed payments hurt credit score significantly. Set up autopay for minimums.")

    # Calculate weighted overall score
    overall = sum(c["score"] * c["weight"] for c in components.values())
    overall = round(overall)

    # Grade
    if overall >= 90:
        grade = "A"
    elif overall >= 75:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    # Trend
    if debt_change_30d < -100:
        trend = "improving"
    elif debt_change_30d > 100:
        trend = "declining"
    else:
        trend = "stable"

    if not tips:
        tips.append("Great job! Keep up your current financial habits.")

    return HealthScoreBreakdown(
        overall_score=overall,
        grade=grade,
        components=components,
        tips=tips,
        trend=trend,
    )
