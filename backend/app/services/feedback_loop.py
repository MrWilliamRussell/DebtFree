"""User feedback loop for continuous LLM improvement.

Stores thumbs-up/down + comments on predictions and categorizations,
enabling periodic retraining and Qdrant embedding updates.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50))  # "categorization", "forecast", "waste_score", "nudge"
    entity_id: Mapped[int] = mapped_column(nullable=True)
    original_value: Mapped[str] = mapped_column(Text, default="")
    corrected_value: Mapped[str] = mapped_column(Text, default="")
    is_positive: Mapped[bool] = mapped_column(Boolean)  # thumbs up = True
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def build_training_examples(feedback_records: list[UserFeedback]) -> list[dict]:
    """Convert user feedback into training examples for LoRA fine-tuning.

    Returns list of {input, output} pairs for supervised fine-tuning.
    """
    examples = []
    for fb in feedback_records:
        if fb.entity_type == "categorization" and fb.corrected_value:
            examples.append({
                "input": fb.original_value,
                "output": fb.corrected_value,
                "type": "categorization",
            })
        elif fb.entity_type == "waste_score" and fb.corrected_value:
            examples.append({
                "input": fb.original_value,
                "output": fb.corrected_value,
                "type": "waste_scoring",
            })

    return examples


def calculate_accuracy_metrics(feedback_records: list[UserFeedback]) -> dict:
    """Calculate model accuracy from user feedback."""
    by_type: dict[str, dict] = {}

    for fb in feedback_records:
        if fb.entity_type not in by_type:
            by_type[fb.entity_type] = {"positive": 0, "negative": 0, "total": 0}
        by_type[fb.entity_type]["total"] += 1
        if fb.is_positive:
            by_type[fb.entity_type]["positive"] += 1
        else:
            by_type[fb.entity_type]["negative"] += 1

    metrics = {}
    for entity_type, counts in by_type.items():
        accuracy = counts["positive"] / counts["total"] * 100 if counts["total"] > 0 else 0
        metrics[entity_type] = {
            "accuracy": round(accuracy, 1),
            "total_feedback": counts["total"],
            "positive": counts["positive"],
            "negative": counts["negative"],
        }

    return metrics
