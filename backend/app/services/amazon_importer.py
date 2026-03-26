"""Amazon order history importer.

Amazon doesn't provide a public API for order history.
Users must manually export their data via:
  1. Amazon.com → Account → Download order reports (CSV)
  2. Amazon.com → Account → Request Your Data (full export)

This module parses both formats and auto-categorizes each item using
the LLM + rule-based hybrid approach.
"""

import io
from datetime import date
import pandas as pd

from app.models.transaction import TransactionType, TransactionCategory

# Amazon-specific category keywords
AMAZON_CATEGORY_RULES = {
    # Electronics
    "headphone": TransactionCategory.ENTERTAINMENT,
    "speaker": TransactionCategory.ENTERTAINMENT,
    "charger": TransactionCategory.SHOPPING,
    "cable": TransactionCategory.SHOPPING,
    "phone case": TransactionCategory.SHOPPING,
    "laptop": TransactionCategory.SHOPPING,
    "tablet": TransactionCategory.SHOPPING,
    "kindle": TransactionCategory.SUBSCRIPTIONS,
    # Groceries (Whole Foods / Amazon Fresh)
    "whole foods": TransactionCategory.GROCERIES,
    "amazon fresh": TransactionCategory.GROCERIES,
    "grocery": TransactionCategory.GROCERIES,
    "food": TransactionCategory.GROCERIES,
    "snack": TransactionCategory.GROCERIES,
    # Subscriptions
    "prime membership": TransactionCategory.SUBSCRIPTIONS,
    "prime video": TransactionCategory.SUBSCRIPTIONS,
    "audible": TransactionCategory.SUBSCRIPTIONS,
    "kindle unlimited": TransactionCategory.SUBSCRIPTIONS,
    "subscribe & save": TransactionCategory.GROCERIES,
    # Household
    "cleaning": TransactionCategory.SHOPPING,
    "paper towel": TransactionCategory.SHOPPING,
    "toilet paper": TransactionCategory.SHOPPING,
    "detergent": TransactionCategory.SHOPPING,
    "soap": TransactionCategory.SHOPPING,
    # Clothing
    "shirt": TransactionCategory.CLOTHING,
    "pants": TransactionCategory.CLOTHING,
    "shoes": TransactionCategory.CLOTHING,
    "jacket": TransactionCategory.CLOTHING,
    "socks": TransactionCategory.CLOTHING,
    # Health
    "vitamin": TransactionCategory.MEDICAL,
    "supplement": TransactionCategory.MEDICAL,
    "medicine": TransactionCategory.MEDICAL,
    "bandage": TransactionCategory.MEDICAL,
    "first aid": TransactionCategory.MEDICAL,
}

ESSENTIAL_CATEGORIES = {
    TransactionCategory.GROCERIES,
    TransactionCategory.MEDICAL,
}


def categorize_amazon_item(title: str) -> TransactionCategory:
    """Categorize an Amazon item by its product title."""
    title_lower = title.lower()
    for keyword, category in AMAZON_CATEGORY_RULES.items():
        if keyword in title_lower:
            return category
    return TransactionCategory.AMAZON


def parse_amazon_order_csv(csv_bytes: bytes) -> list[dict]:
    """Parse Amazon's "Order History Reports" CSV format.

    Expected columns vary but typically include:
    - Order Date, Order ID, Title/Product Name, Item Total, Category
    """
    df = pd.read_csv(io.BytesIO(csv_bytes))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Detect column names (Amazon changes format occasionally)
    date_col = _find_col(df, ["order_date", "date", "order_placed"])
    title_col = _find_col(df, ["title", "product_name", "item_description", "product"])
    amount_col = _find_col(df, ["item_total", "total", "amount", "price", "item_subtotal"])

    if not date_col or not amount_col:
        raise ValueError(
            "Could not find required columns. Expected 'order_date'/'date' and 'item_total'/'amount'. "
            f"Found columns: {list(df.columns)}"
        )

    results = []
    for _, row in df.iterrows():
        try:
            order_date = pd.to_datetime(row[date_col]).date()
            amount_str = str(row[amount_col]).replace("$", "").replace(",", "").strip()
            if not amount_str or amount_str in ("nan", ""):
                continue
            amount = abs(float(amount_str))
            title = str(row.get(title_col, "Amazon Purchase")) if title_col else "Amazon Purchase"
            category = categorize_amazon_item(title)

            results.append({
                "date": order_date,
                "amount": amount,
                "description": title[:500],
                "merchant": "Amazon",
                "transaction_type": TransactionType.EXPENSE,
                "category": category,
                "is_essential": category in ESSENTIAL_CATEGORIES,
                "is_recurring": "subscribe" in title.lower(),
            })
        except Exception:
            continue

    return results


def parse_amazon_data_export(csv_bytes: bytes) -> list[dict]:
    """Parse Amazon's 'Request Your Data' export format.

    This is the larger data export from Account → Request Your Data → Orders.
    Format includes: Digital Orders.csv, Retail.OrderHistory.csv, etc.
    """
    # Try parsing as the retail order history format
    return parse_amazon_order_csv(csv_bytes)


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column name from a list of candidates."""
    for c in candidates:
        if c in df.columns:
            return c
        # Fuzzy match
        for actual in df.columns:
            if c in actual or actual in c:
                return actual
    return None
