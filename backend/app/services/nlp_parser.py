"""Natural language transaction parser using Ollama local LLM.

Parses casual inputs like "Spent $45 on gas yesterday at Shell" into structured transactions.
"""

import json
import re
from datetime import date, timedelta
from ollama import AsyncClient

from app.config import settings

PARSE_PROMPT = """You are a financial transaction parser. Extract structured data from the user's natural language input.

Return ONLY valid JSON with these fields:
- amount: number (always positive)
- transaction_type: "expense" or "income"
- category: one of [rent, mortgage, utilities, groceries, gas, insurance, medical, dining, entertainment, shopping, amazon, subscriptions, clothing, travel, debt_payment, savings, investment, income, transfer, other]
- description: brief description
- merchant: merchant/store name if mentioned
- date: ISO date string (YYYY-MM-DD). Use {today} as today's date. "yesterday" = {yesterday}, "last week" = {last_week}
- is_essential: boolean (true for rent, mortgage, utilities, groceries, gas, insurance, medical)
- is_recurring: boolean (true if they mention it's monthly/weekly/regular)

Input: "{input}"

JSON:"""


async def parse_natural_language(text: str) -> dict:
    """Parse a natural language transaction description into structured data."""
    today = date.today()
    prompt = PARSE_PROMPT.format(
        input=text,
        today=today.isoformat(),
        yesterday=(today - timedelta(days=1)).isoformat(),
        last_week=(today - timedelta(days=7)).isoformat(),
    )

    client = AsyncClient(host=settings.ollama_base_url)
    response = await client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1},
    )

    content = response["message"]["content"]

    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'\{[\s\S]*\}', content)
    if not json_match:
        raise ValueError(f"Could not parse LLM response: {content}")

    return json.loads(json_match.group())


async def categorize_transaction(description: str, merchant: str) -> str:
    """Use LLM to categorize a transaction when rule-based matching fails."""
    prompt = f"""Categorize this financial transaction into exactly one category.

Categories: rent, mortgage, utilities, groceries, gas, insurance, medical, dining, entertainment, shopping, amazon, subscriptions, clothing, travel, debt_payment, savings, investment, income, transfer, other

Transaction: "{description}" at "{merchant}"

Reply with ONLY the category name, nothing else."""

    client = AsyncClient(host=settings.ollama_base_url)
    response = await client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.0},
    )

    category = response["message"]["content"].strip().lower().replace(" ", "_")
    valid = {
        "rent", "mortgage", "utilities", "groceries", "gas", "insurance", "medical",
        "dining", "entertainment", "shopping", "amazon", "subscriptions", "clothing",
        "travel", "debt_payment", "savings", "investment", "income", "transfer", "other",
    }
    return category if category in valid else "other"


async def generate_waste_score(transactions_summary: str) -> dict:
    """Analyze spending patterns and score categories for waste potential."""
    prompt = f"""You are a personal finance advisor. Analyze this monthly spending summary and score each discretionary category for "waste potential" (0-100, where 100 = highest waste).

Spending summary:
{transactions_summary}

For each discretionary category, provide:
- waste_score: 0-100
- reason: one sentence why
- suggestion: one actionable cut suggestion
- monthly_savings_estimate: dollar amount that could reasonably be saved

Return ONLY valid JSON as a list of objects. Example:
[{{"category": "dining", "waste_score": 75, "reason": "Eating out 18 times exceeds typical needs", "suggestion": "Meal prep 3 days/week to cut dining by 40%", "monthly_savings_estimate": 180}}]

JSON:"""

    client = AsyncClient(host=settings.ollama_base_url)
    response = await client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3},
    )

    content = response["message"]["content"]
    json_match = re.search(r'\[[\s\S]*\]', content)
    if not json_match:
        return []

    return json.loads(json_match.group())
