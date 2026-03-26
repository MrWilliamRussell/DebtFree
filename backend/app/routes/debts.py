from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.debt import Debt
from app.schemas import DebtCreate, DebtOut, PayoffRequest, PayoffResult
from app.services.debt_engine import calculate_payoff_plan

router = APIRouter()


@router.get("/", response_model=list[DebtOut])
async def list_debts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Debt).where(Debt.is_active == True))
    return result.scalars().all()


@router.post("/", response_model=DebtOut, status_code=201)
async def create_debt(data: DebtCreate, db: AsyncSession = Depends(get_db)):
    debt = Debt(**data.model_dump())
    db.add(debt)
    await db.commit()
    await db.refresh(debt)
    return debt


@router.put("/{debt_id}", response_model=DebtOut)
async def update_debt(debt_id: int, data: DebtCreate, db: AsyncSession = Depends(get_db)):
    debt = await db.get(Debt, debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    for key, val in data.model_dump().items():
        setattr(debt, key, val)
    await db.commit()
    await db.refresh(debt)
    return debt


@router.post("/payoff-plan", response_model=PayoffResult)
async def get_payoff_plan(req: PayoffRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = result.scalars().all()
    if not debts:
        raise HTTPException(status_code=400, detail="No active debts found")
    return calculate_payoff_plan(debts, req.strategy, req.extra_monthly_payment)
