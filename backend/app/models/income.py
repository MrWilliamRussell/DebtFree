import enum
from datetime import datetime, date
from sqlalchemy import String, Numeric, DateTime, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IncomeFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


class Income(Base):
    __tablename__ = "incomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    frequency: Mapped[IncomeFrequency] = mapped_column(Enum(IncomeFrequency))
    next_pay_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
