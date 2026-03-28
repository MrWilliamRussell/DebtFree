from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.transaction import Transaction, TransactionCategory
from app.schemas import TransactionCreate, TransactionOut
from app.services.discord_alerts import check_budget_and_alert

router = APIRouter()


@router.get("/", response_model=list[TransactionOut])
async def list_transactions(
    account_id: Optional[int] = None,
    category: Optional[TransactionCategory] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    query = select(Transaction)
    filters = []
    if account_id:
        filters.append(Transaction.account_id == account_id)
    if category:
        filters.append(Transaction.category == category)
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(Transaction.date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=TransactionOut, status_code=201)
async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)) -> TransactionOut:
    transaction = Transaction(**data.model_dump())
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    check_budget_and_alert(transaction, db)  # Assuming this function is defined elsewhere
    return transaction


@router.put("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int, data: TransactionCreate, db: AsyncSession = Depends(get_db)
) -> TransactionOut:
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, val in data.model_dump().items():
        setattr(transaction, key, val)
    await db.commit()
    await db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(transaction)
    await db.commit()