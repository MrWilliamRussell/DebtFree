"""Forecasting and debt-free timeline routes."""

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
from app.schemas import ForecastRequest, ForecastResponse, CategoryForecast, DebtFreeProjection
from app.services.forecasting import forecast_category_spending, forecast_debt_free_date
from app.routes.dashboard import monthly_income_amount

router = APIRouter()


@router.post("/spending", response_model=ForecastResponse)
async def forecast_spending(req: ForecastRequest, db: AsyncSession = Depends(get_db)):
    """Forecast future spending by category using time-series models."""
    today = date.today()

    # Get 12 months of transaction history
    start = today - timedelta(days=365)
    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= start,
            )
        )
    )
    transactions = result.scalars().all()

    # Group by category and month
    by_cat_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        month_key = t.date.strftime("%Y-%m")
        by_cat_month[t.category.value][month_key] += float(t.amount)

    # Build month labels for forecast
    forecast_labels = []
    for i in range(1, req.months_ahead + 1):
        future = today + relativedelta(months=i)
        forecast_labels.append(future.strftime("%Y-%m"))

    # Filter categories if specified
    categories = req.categories or list(by_cat_month.keys())

    category_forecasts = []
    alert_categories = []
    total_predicted_change = 0
    total_categories = 0

    for cat in categories:
        if cat not in by_cat_month:
            continue

        # Build ordered monthly values
        month_data = by_cat_month[cat]
        all_months = sorted(month_data.keys())
        values = [month_data.get(m, 0) for m in all_months]

        if not values:
            continue

        forecast = forecast_category_spending(values, req.months_ahead, forecast_labels)

        category_forecasts.append(CategoryForecast(
            category=cat,
            months=forecast.months_ahead,
            predicted=forecast.predicted_values,
            lower_bound=forecast.lower_bound,
            upper_bound=forecast.upper_bound,
            trend=forecast.trend,
            pct_change=forecast.pct_change,
        ))

        total_predicted_change += forecast.pct_change
        total_categories += 1

        # Flag rising categories
        if forecast.pct_change > 25:
            alert_categories.append({
                "category": cat,
                "pct_change": forecast.pct_change,
                "trend": forecast.trend,
                "message": f"{cat} predicted to rise {forecast.pct_change:.0f}% — consider preemptive cuts",
            })

    # Overall trend
    avg_change = total_predicted_change / total_categories if total_categories > 0 else 0
    if avg_change > 10:
        overall_trend = "rising"
    elif avg_change < -10:
        overall_trend = "falling"
    else:
        overall_trend = "stable"

    # Debt-free projection
    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min = sum(float(d.minimum_payment) for d in debts)
    avg_rate = (sum(float(d.interest_rate) for d in debts) / len(debts)) if debts else 0

    incomes_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = incomes_result.scalars().all()
    monthly_income = sum(monthly_income_amount(i) for i in incomes)

    # Current month expenses
    month_start = today.replace(day=1)
    expenses_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= month_start,
            )
        )
    )
    current_expenses = sum(float(t.amount) for t in expenses_result.scalars().all())

    scenarios = forecast_debt_free_date(
        total_debt=total_debt,
        monthly_payment=total_min,
        avg_interest_rate=avg_rate,
        monthly_income=monthly_income,
        monthly_expenses=current_expenses,
        forecast_expense_change_pct=avg_change,
    )

    projection = DebtFreeProjection(
        current_months=scenarios["current"]["months_to_payoff"],
        current_interest=scenarios["current"]["total_interest"],
        optimistic_months=scenarios["optimistic_15pct_cut"]["months_to_payoff"],
        optimistic_interest=scenarios["optimistic_15pct_cut"]["total_interest"],
        forecasted_months=scenarios["forecasted"]["months_to_payoff"],
        forecasted_interest=scenarios["forecasted"]["total_interest"],
    )

    return ForecastResponse(
        category_forecasts=category_forecasts,
        debt_free_projection=projection,
        overall_expense_trend=overall_trend,
        alert_categories=alert_categories,
    )
