from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, and_

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.debt import Debt
from app.models.income import Income, IncomeFrequency
from app.schemas import DashboardSummary, IncomeCreate, IncomeOut

router = APIRouter()

ESSENTIAL_CATEGORIES = {
    TransactionCategory.RENT,
    TransactionCategory.MORTGAGE,
    TransactionCategory.UTILITIES,
    TransactionCategory.GROCERIES,
    TransactionCategory.GAS,
    TransactionCategory.INSURANCE,
    TransactionCategory.MEDICAL,
}


def monthly_income_amount(income: Income) -> float:
    """Convert any income frequency to a monthly amount."""
    multipliers = {
        IncomeFrequency.WEEKLY: 52 / 12,
        IncomeFrequency.BIWEEKLY: 26 / 12,
        IncomeFrequency.SEMIMONTHLY: 2,
        IncomeFrequency.MONTHLY: 1,
        IncomeFrequency.ANNUAL: 1 / 12,
        IncomeFrequency.ONE_TIME: 0,
    }
    return float(income.amount) * multipliers.get(income.frequency, 1)


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)

    # Monthly income from income sources
    incomes_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = incomes_result.scalars().all()
    total_income_monthly = sum(monthly_income_amount(i) for i in incomes)

    # Monthly expenses from transactions this month
    expenses_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= month_start,
                Transaction.date <= today,
            )
        )
    )
    expenses = expenses_result.scalars().all()
    total_expenses_monthly = sum(float(t.amount) for t in expenses)

    # Expenses by category
    by_category: dict[str, float] = {}
    essential_total = 0.0
    discretionary_total = 0.0
    for t in expenses:
        cat = t.category.value
        by_category[cat] = by_category.get(cat, 0) + float(t.amount)
        if t.category in ESSENTIAL_CATEGORIES:
            essential_total += float(t.amount)
        else:
            discretionary_total += float(t.amount)

    # Total debt
    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min_payments = sum(float(d.minimum_payment) for d in debts)

    # Debt-to-income ratio
    dti = (total_min_payments / total_income_monthly * 100) if total_income_monthly > 0 else 0

    # Top categories to cut (discretionary, sorted highest first)
    discretionary_cats = {
        k: v for k, v in by_category.items()
        if TransactionCategory(k) not in ESSENTIAL_CATEGORIES
    }
    top_cuts = [
        {"category": k, "amount": v, "suggestion": f"Consider reducing {k} spending (${v:.2f}/mo)"}
        for k, v in sorted(discretionary_cats.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return DashboardSummary(
        total_income_monthly=round(total_income_monthly, 2),
        total_expenses_monthly=round(total_expenses_monthly, 2),
        net_monthly=round(total_income_monthly - total_expenses_monthly, 2),
        total_debt=round(total_debt, 2),
        total_minimum_payments=round(total_min_payments, 2),
        debt_to_income_ratio=round(dti, 2),
        expenses_by_category=by_category,
        essential_vs_discretionary={
            "essential": round(essential_total, 2),
            "discretionary": round(discretionary_total, 2),
        },
        top_cuts=top_cuts,
    )


# ── Income endpoints (grouped with dashboard) ──
@router.get("/incomes", response_model=list[IncomeOut])
async def list_incomes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Income).where(Income.is_active == True))
    return result.scalars().all()


@router.post("/incomes", response_model=IncomeOut, status_code=201)
async def create_income(data: IncomeCreate, db: AsyncSession = Depends(get_db)):
    income = Income(**data.model_dump())
    db.add(income)
    await db.commit()
    await db.refresh(income)
    return income
