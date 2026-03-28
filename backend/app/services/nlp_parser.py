import json
import re
from datetime import date, timedelta
from typing import Any, Dict

from ollama import AsyncClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tenacity import retry, wait_exponential, stop_after_attempt, TimeoutError as RetryTimeoutError

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


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
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
        timeout=10  # seconds
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
        timeout=10  # seconds
    )

    category = response["message"]["content"].strip().lower().replace(" ", "_")
    valid_categories = {
        "rent", "mortgage", "utilities", "groceries", "gas", "insurance", "medical",
        "dining", "entertainment", "shopping", "amazon", "subscriptions", "clothing",
        "travel", "debt_payment", "savings", "investment", "income", "transfer", "other"
    }
    if category not in valid_categories:
        raise ValueError(f"Invalid category: {category}")
    return category


_client: QdrantClient | None = None
_model: SentenceTransformer | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
def ensure_collection_exists():
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if settings.COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
def index_transaction(txn_id: int, description: str, merchant: str, category: str):
    """Embed and store a transaction for semantic search."""
    client = get_qdrant_client()
    model = get_embedding_model()
    text = f"{description} {merchant} {category}"
    embedding = model.encode([text])[0].tolist()

    point = PointStruct(
        id=txn_id,
        vector=embedding,
        payload={
            "description": description,
            "merchant": merchant,
            "category": category
        }
    )

    client.upsert(collection_name=settings.COLLECTION_NAME, points=[