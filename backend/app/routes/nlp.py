"""Natural language transaction entry route."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.schemas import NLPTransactionInput, NLPParseResult, TransactionOut
from app.services.nlp_parser import parse_natural_language
from app.services.discord_alerts import check_budget_and_alert

router = APIRouter()

ESSENTIAL_CATEGORIES = {"rent", "mortgage", "utilities", "groceries", "gas", "insurance", "medical"}


@router.post("/parse", response_model=NLPParseResult)
async def parse_transaction(data: NLPTransactionInput):
    """Parse natural language into a structured transaction (preview, no save)."""
    try:
        parsed = await parse_natural_language(data.text)
        # Validate required fields
        has_amount = "amount" in parsed and parsed["amount"] > 0
        has_category = "category" in parsed and parsed["category"] != "other"
        confidence = "high" if (has_amount and has_category) else "medium" if has_amount else "low"

        return NLPParseResult(
            parsed=parsed,
            confidence=confidence,
            needs_review=confidence != "high",
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse: {str(e)}")


@router.post("/parse-and-save", response_model=TransactionOut)
async def parse_and_save(data: NLPTransactionInput, db: AsyncSession = Depends(get_db)):
    """Parse natural language and immediately save the transaction."""
    try:
        parsed = await parse_natural_language(data.text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse: {str(e)}")

    txn_type = TransactionType(parsed.get("transaction_type", "expense"))
    category_str = parsed.get("category", "other")
    try:
        category = TransactionCategory(category_str)
    except ValueError:
        category = TransactionCategory.OTHER

    txn = Transaction(
        account_id=data.account_id,
        date=date.fromisoformat(parsed.get("date", date.today().isoformat())),
        amount=abs(float(parsed.get("amount", 0))),
        transaction_type=txn_type,
        category=category,
        description=parsed.get("description", data.text),
        merchant=parsed.get("merchant", ""),
        is_recurring=parsed.get("is_recurring", False),
        is_essential=category_str in ESSENTIAL_CATEGORIES,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    await check_budget_and_alert(db, txn)
    return txn
