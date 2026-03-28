"""Financial health score and coaching routes."""

from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import asyncio

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.debt import Debt
from app.models.income import Income
from app.schemas import HealthScoreResponse, CoachingNudge, FullHealthResponse
from app.services.health_score import calculate_health_score
from app.services.coaching import generate_daily_nudge
from app.routes.dashboard import monthly_income_amount, ESSENTIAL_CATEGORIES

router = APIRouter()

# Mock functions to simulate health checks for external services
async def check_postgresql():
    # Simulate a database connection check
    await asyncio.sleep(0.1)
    return {"status": "healthy", "latency": 0.1}

async def check_qdrant():
    # Simulate a Qdrant service check
    await asyncio.sleep(0.2)
    return {"status": "degraded", "latency": 0.2}

async def check_ollama():
    # Simulate an Ollama service check
    await asyncio.sleep(0.3)
    return {"status": "healthy", "latency": 0.3}

async def check_redis():
    # Simulate a Redis service check
    await asyncio.sleep(0.15)
    return {"status": "unhealthy", "latency": 0.15}

async def check_plaid():
    # Simulate a Plaid service check
    await asyncio.sleep(0.25)
    return {"status": "healthy", "latency": 0.25}

@router.get("/score", response_model=HealthScoreResponse)
async def get_health_score(db: AsyncSession = Depends(get_db)):
    """Calculate comprehensive financial health score."""
    today = date.today()
    month_start = today.replace(day=1)

    # Income
    incomes_result = await db.execute(select(Income).where(Income.is_active == True))
    incomes = incomes_result.scalars().all()
    monthly_income = sum(monthly_income_amount(i) for i in incomes)

    # Expenses this month
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

    # Debt
    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min = sum(float(d.minimum_payment) for d in debts)

    result = calculate_health_score(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        total_debt=total_debt,
        total_minimum_payments=total_min,
        essential_expenses=essential,
        discretionary_expenses=discretionary,
    )

    return HealthScoreResponse(
        overall_score=result.overall_score,
        grade=result.grade,
        components=result.components,
        tips=result.tips,
        trend=result.trend,
    )


@router.get("/nudge", response_model=CoachingNudge)
async def get_coaching_nudge(db: AsyncSession = Depends(get_db)):
    """Get an AI-generated coaching nudge for today."""
    today = date.today()
    month_start = today.replace(day=1)

    # Quick stats for the coach
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

    # Debt
    debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = debts_result.scalars().all()
    total_debt = sum(float(d.current_balance) for d in debts)
    total_min = sum(float(d.minimum_payment) for d in debts)

    nudge = generate_daily_nudge(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        total_debt=total_debt,
        total_minimum_payments=total_min,
        essential_expenses=essential,
        discretionary_expenses=discretionary,
    )

    return CoachingNudge(nudge=nudge)


@router.get("/health/full", response_model=FullHealthResponse)
async def get_full_health():
    """Check the health of all external services and return an aggregated status."""
    tasks = [
        check_postgresql(),
        check_qdrant(),
        check_ollama(),
        check_redis(),
        check_plaid()
    ]
    
    results = await asyncio.gather(*tasks)

    postgresql_status = results[0]
    qdrant_status = results[1]
    ollama_status = results[2]
    redis_status = results[3]
    plaid_status