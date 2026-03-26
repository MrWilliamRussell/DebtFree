"""Qdrant vector search for transaction indexing and smart categorization."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from app.config import settings

COLLECTION_NAME = "transactions"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension

_client: QdrantClient | None = None
_model: SentenceTransformer | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, prefer_grpc=True)
    return _client


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def ensure_collection():
    """Create the transactions collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def index_transaction(txn_id: int, description: str, merchant: str, category: str):
    """Embed and store a transaction for semantic search."""
    client = get_qdrant_client()
    model = get_embedding_model()
    text = f"{description} {merchant} {category}"
    vector = model.encode(text).tolist()

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=txn_id,
                vector=vector,
                payload={
                    "description": description,
                    "merchant": merchant,
                    "category": category,
                },
            )
        ],
    )


def search_similar_transactions(query: str, limit: int = 10) -> list[dict]:
    """Find transactions similar to a query string."""
    client = get_qdrant_client()
    model = get_embedding_model()
    vector = model.encode(query).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
    )
    return [
        {"id": r.id, "score": r.score, **r.payload}
        for r in results.points
    ]
