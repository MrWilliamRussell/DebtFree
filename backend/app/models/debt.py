import enum
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PayoffStrategy(str, enum.Enum):
    AVALANCHE = "avalanche"  # Highest interest first
    SNOWBALL = "snowball"    # Smallest balance first


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    current_balance: Mapped[float] = mapped_column(Numeric(12, 2))
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 2))
    minimum_payment: Mapped[float] = mapped_column(Numeric(10, 2))
    credit_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    due_day: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
