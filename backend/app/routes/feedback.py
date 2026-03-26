"""User feedback routes for LLM improvement loop."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.feedback_loop import UserFeedback, calculate_accuracy_metrics
from app.schemas import FeedbackCreate, FeedbackOut, AccuracyMetrics

router = APIRouter()


@router.post("/", response_model=FeedbackOut, status_code=201)
async def submit_feedback(data: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    """Submit thumbs-up/down feedback on a prediction or categorization."""
    fb = UserFeedback(**data.model_dump())
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


@router.get("/metrics", response_model=AccuracyMetrics)
async def get_accuracy_metrics(db: AsyncSession = Depends(get_db)):
    """Get accuracy metrics calculated from user feedback."""
    result = await db.execute(select(UserFeedback))
    records = result.scalars().all()
    metrics = calculate_accuracy_metrics(records)
    return AccuracyMetrics(metrics=metrics)
