from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.budget import Budget
from app.schemas import BudgetCreate, BudgetOut

router = APIRouter()


@router.get("/", response_model=list[BudgetOut])
async def list_budgets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Budget).where(Budget.is_active == True))
    return result.scalars().all()


@router.post("/", response_model=BudgetOut, status_code=201)
async def create_budget(data: BudgetCreate, db: AsyncSession = Depends(get_db)):
    budget = Budget(**data.model_dump())
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(budget_id: int, data: BudgetCreate, db: AsyncSession = Depends(get_db)):
    budget = await db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for key, val in data.model_dump().items():
        setattr(budget, key, val)
    await db.commit()
    await db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(budget_id: int, db: AsyncSession = Depends(get_db)):
    budget = await db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget.is_active = False
    await db.commit()
