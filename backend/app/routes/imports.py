"""CSV import routes — bank exports, credit cards, and Amazon order history.

All paths use a hybrid categorization pipeline:
1. Rule-based keyword matching (instant, 50+ merchant rules)
2. LLM fallback via Ollama for uncategorized ("other") transactions
"""

import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.database import get_db
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.services.nlp_parser import categorize_transaction
from app.services.amazon_importer import parse_amazon_order_csv

router = APIRouter()

# ── Rule-based keyword → category mapping ──
CATEGORY_RULES = {
    "amazon": TransactionCategory.AMAZON,
    "whole foods": TransactionCategory.GROCERIES,
    "walmart": TransactionCategory.GROCERIES,
    "costco": TransactionCategory.GROCERIES,
    "kroger": TransactionCategory.GROCERIES,
    "trader joe": TransactionCategory.GROCERIES,
    "aldi": TransactionCategory.GROCERIES,
    "safeway": TransactionCategory.GROCERIES,
    "target": TransactionCategory.SHOPPING,
    "shell": TransactionCategory.GAS,
    "chevron": TransactionCategory.GAS,
    "arco": TransactionCategory.GAS,
    "exxon": TransactionCategory.GAS,
    "76": TransactionCategory.GAS,
    "bp ": TransactionCategory.GAS,
    "circle k": TransactionCategory.GAS,
    "speedway": TransactionCategory.GAS,
    "netflix": TransactionCategory.SUBSCRIPTIONS,
    "spotify": TransactionCategory.SUBSCRIPTIONS,
    "hulu": TransactionCategory.SUBSCRIPTIONS,
    "disney+": TransactionCategory.SUBSCRIPTIONS,
    "disney plus": TransactionCategory.SUBSCRIPTIONS,
    "youtube": TransactionCategory.SUBSCRIPTIONS,
    "apple.com/bill": TransactionCategory.SUBSCRIPTIONS,
    "hbo": TransactionCategory.SUBSCRIPTIONS,
    "paramount": TransactionCategory.SUBSCRIPTIONS,
    "peacock": TransactionCategory.SUBSCRIPTIONS,
    "adobe": TransactionCategory.SUBSCRIPTIONS,
    "microsoft": TransactionCategory.SUBSCRIPTIONS,
    "uber eats": TransactionCategory.DINING,
    "doordash": TransactionCategory.DINING,
    "grubhub": TransactionCategory.DINING,
    "starbucks": TransactionCategory.DINING,
    "mcdonald": TransactionCategory.DINING,
    "chipotle": TransactionCategory.DINING,
    "chick-fil-a": TransactionCategory.DINING,
    "taco bell": TransactionCategory.DINING,
    "subway": TransactionCategory.DINING,
    "pizza": TransactionCategory.DINING,
    "rent": TransactionCategory.RENT,
    "mortgage": TransactionCategory.MORTGAGE,
    "insurance": TransactionCategory.INSURANCE,
    "geico": TransactionCategory.INSURANCE,
    "state farm": TransactionCategory.INSURANCE,
    "allstate": TransactionCategory.INSURANCE,
    "progressive": TransactionCategory.INSURANCE,
    "electric": TransactionCategory.UTILITIES,
    "water": TransactionCategory.UTILITIES,
    "pg&e": TransactionCategory.UTILITIES,
    "edison": TransactionCategory.UTILITIES,
    "at&t": TransactionCategory.UTILITIES,
    "verizon": TransactionCategory.UTILITIES,
    "t-mobile": TransactionCategory.UTILITIES,
    "xfinity": TransactionCategory.UTILITIES,
    "comcast": TransactionCategory.UTILITIES,
    "spectrum": TransactionCategory.UTILITIES,
    "cvs": TransactionCategory.MEDICAL,
    "walgreens": TransactionCategory.MEDICAL,
    "pharmacy": TransactionCategory.MEDICAL,
    "doctor": TransactionCategory.MEDICAL,
    "hospital": TransactionCategory.MEDICAL,
    "dental": TransactionCategory.MEDICAL,
}

ESSENTIAL_CATEGORIES = {
    TransactionCategory.RENT, TransactionCategory.MORTGAGE,
    TransactionCategory.UTILITIES, TransactionCategory.GROCERIES,
    TransactionCategory.GAS, TransactionCategory.INSURANCE,
    TransactionCategory.MEDICAL,
}


def auto_categorize(description: str) -> TransactionCategory:
    """Rule-based categorization. Returns OTHER if no match (triggers LLM fallback)."""
    desc_lower = description.lower()
    for keyword, category in CATEGORY_RULES.items():
        if keyword in desc_lower:
            return category
    return TransactionCategory.OTHER


async def smart_categorize(description: str, merchant: str) -> TransactionCategory:
    """Hybrid categorization: rules first, LLM fallback for unknowns."""
    # Step 1: Rule-based (fast)
    category = auto_categorize(description)
    if category != TransactionCategory.OTHER:
        return category

    # Step 2: Try merchant name rules
    if merchant:
        category = auto_categorize(merchant)
        if category != TransactionCategory.OTHER:
            return category

    # Step 3: LLM fallback (slower, but handles edge cases)
    try:
        llm_cat = await categorize_transaction(description, merchant)
        return TransactionCategory(llm_cat)
    except Exception:
        return TransactionCategory.OTHER


@router.post("/csv")
async def import_csv(
    account_id: int,
    file: UploadFile = File(...),
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Import transactions from a bank/credit card CSV export.

    Hybrid categorization: instant rule matching + LLM for unknowns.
    Set use_llm=false to skip LLM (faster, less accurate).
    """
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    df.columns = [c.strip().lower() for c in df.columns]

    date_col = next((c for c in df.columns if "date" in c), None)
    if not date_col:
        raise HTTPException(status_code=400, detail="CSV must contain a 'date' column")

    desc_col = next((c for c in df.columns if c in ("description", "memo", "name", "merchant", "payee")), None)
    if not desc_col:
        desc_col = next((c for c in df.columns if "desc" in c), "description")

    amount_col = next((c for c in df.columns if "amount" in c), None)
    if not amount_col:
        raise HTTPException(status_code=400, detail="CSV must contain an 'amount' column")

    imported = 0
    llm_categorized = 0

    for _, row in df.iterrows():
        try:
            txn_date = pd.to_datetime(row[date_col]).date()
            amount = float(str(row[amount_col]).replace("$", "").replace(",", ""))
            description = str(row.get(desc_col, ""))

            txn_type = TransactionType.EXPENSE if amount < 0 else TransactionType.INCOME

            # Hybrid categorization
            if use_llm:
                category = await smart_categorize(description, description[:300])
                if category != TransactionCategory.OTHER:
                    llm_categorized += 1
            else:
                category = auto_categorize(description)

            txn = Transaction(
                account_id=account_id,
                date=txn_date,
                amount=abs(amount),
                transaction_type=txn_type,
                category=category,
                description=description,
                merchant=description[:300],
                is_essential=category in ESSENTIAL_CATEGORIES,
            )
            db.add(txn)
            imported += 1
        except Exception:
            continue

    await db.commit()
    return {
        "imported": imported,
        "total_rows": len(df),
        "llm_categorized": llm_categorized,
    }


@router.post("/amazon")
async def import_amazon(
    account_id: int,
    file: UploadFile = File(...),
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Import Amazon order history CSV.

    Download from: Amazon.com → Account → Download order reports
    Or: Amazon.com → Account → Request Your Data
    """
    content = await file.read()
    try:
        orders = parse_amazon_order_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    imported = 0
    llm_categorized = 0

    for order in orders:
        category = order["category"]

        # LLM fallback for uncategorized Amazon items
        if use_llm and category == TransactionCategory.AMAZON:
            try:
                llm_cat = await categorize_transaction(order["description"], "Amazon")
                category = TransactionCategory(llm_cat)
                llm_categorized += 1
            except Exception:
                category = TransactionCategory.AMAZON

        txn = Transaction(
            account_id=account_id,
            date=order["date"],
            amount=order["amount"],
            transaction_type=TransactionType.EXPENSE,
            category=category,
            description=order["description"],
            merchant="Amazon",
            is_essential=category in ESSENTIAL_CATEGORIES,
            is_recurring=order.get("is_recurring", False),
        )
        db.add(txn)
        imported += 1

    await db.commit()
    return {
        "imported": imported,
        "total_orders": len(orders),
        "llm_categorized": llm_categorized,
    }
