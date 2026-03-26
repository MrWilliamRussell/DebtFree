"""Subscription detection, waste scoring, and cancel/keep recommendations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.transaction import Transaction
from app.models.debt import Debt
from app.models.income import Income
from app.schemas import SubscriptionOut
from app.services.subscription_detector import detect_subscriptions, get_llm_subscription_analysis
from app.services.nlp_parser import generate_waste_score
from app.routes.dashboard import monthly_income_amount

router = APIRouter()


@router.get("/", response_model=list[SubscriptionOut])
async def list_subscriptions(
    lookback_days: int = Query(default=90, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Detect recurring subscriptions with cancel/keep recommendations."""
    result = await db.execute(select(Transaction))
    transactions = result.scalars().all()
    subs = detect_subscriptions(transactions, lookback_days)
    return [
        SubscriptionOut(
            merchant=s.merchant,
            category=s.category,
            avg_amount=s.avg_amount,
            frequency_days=s.frequency_days,
            occurrence_count=s.occurrence_count,
            last_charged=s.last_charged,
            total_spent=s.total_spent,
            waste_score=s.waste_score,
            suggestion=s.suggestion,
            action=s.action,
            cancel_difficulty=s.cancel_difficulty,
            cancel_method=s.cancel_method,
            annual_cost=s.annual_cost,
            alternatives=s.alternatives,
        )
        for s in subs
    ]


@router.get("/waste-analysis")
async def get_waste_analysis(db: AsyncSession = Depends(get_db)):
    """Get LLM-powered deep waste analysis with personalized recommendations."""
    txn_result = await db.execute(select(Transaction))
    transactions = txn_result.scalars().all()
    subs = detect_subscriptions(transactions)

    if not subs:
        return {"subscriptions": [], "total_monthly_waste": 0, "analysis": None}

    # Get income and debt totals for context
    income_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = income_result.scalars().all()
    monthly_income = sum(monthly_income_amount(i) for i in incomes)

    debt_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debt_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)

    # LLM analysis with full financial context
    analysis = await get_llm_subscription_analysis(subs, monthly_income, total_debt)

    total_waste = sum(s.avg_amount for s in subs if s.waste_score >= 50)

    return {
        "subscriptions": [
            {
                "merchant": s.merchant,
                "amount": s.avg_amount,
                "annual_cost": s.annual_cost,
                "waste_score": s.waste_score,
                "action": s.action,
                "suggestion": s.suggestion,
                "cancel_difficulty": s.cancel_difficulty,
                "cancel_method": s.cancel_method,
                "alternatives": s.alternatives,
            }
            for s in subs
        ],
        "total_monthly_waste_potential": round(total_waste, 2),
        "analysis": analysis,
    }
