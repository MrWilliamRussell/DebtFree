"""PDF report generation routes."""

from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.debt import Debt
from app.models.income import Income
from app.services.report_generator import generate_monthly_report
from app.services.health_score import calculate_health_score
from app.routes.dashboard import monthly_income_amount, ESSENTIAL_CATEGORIES

router = APIRouter()


@router.get("/monthly")
async def download_monthly_report(db: AsyncSession = Depends(get_db)):
    """Generate and download a monthly PDF report."""
    today = date.today()
    month_start = today.replace(day=1)
    report_month = today.strftime("%B %Y")

    # Gather all data
    incomes_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = incomes_result.scalars().all()
    monthly_income = sum(monthly_income_amount(i) for i in incomes)

    expenses_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= month_start,
            )
        )
    )
    expenses = expenses_result.scalars().all()
    monthly_expenses = sum(float(t.amount) for t in expenses)
    essential = sum(float(t.amount) for t in expenses if t.category in ESSENTIAL_CATEGORIES)
    discretionary = monthly_expenses - essential

    by_category: dict[str, float] = {}
    for t in expenses:
        cat = t.category.value
        by_category[cat] = by_category.get(cat, 0) + float(t.amount)

    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min = sum(float(d.minimum_payment) for d in debts)

    health = calculate_health_score(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        total_debt=total_debt,
        total_minimum_payments=total_min,
        essential_expenses=essential,
        discretionary_expenses=discretionary,
    )

    pdf_bytes = generate_monthly_report(
        report_month=report_month,
        income=monthly_income,
        expenses=monthly_expenses,
        net=monthly_income - monthly_expenses,
        total_debt=total_debt,
        debt_change=0,
        health_score=health.overall_score,
        grade=health.grade,
        expenses_by_category=by_category,
        payoff_months_remaining=0,
        interest_saved=0,
        tips=health.tips,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=debtfree-report-{today.isoformat()}.pdf"},
    )
