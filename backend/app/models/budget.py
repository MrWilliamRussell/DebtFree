from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.transaction import TransactionCategory


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[TransactionCategory] = mapped_column(Enum(TransactionCategory))
    monthly_limit: Mapped[float] = mapped_column(Numeric(10, 2))
    alert_threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=0.80)  # 80% triggers alert
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
