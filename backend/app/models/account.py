import enum
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    INVESTMENT = "investment"
    CASH = "cash"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType))
    institution: Mapped[str] = mapped_column(String(200), default="")
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    credit_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    minimum_payment: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    due_day: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="account")
