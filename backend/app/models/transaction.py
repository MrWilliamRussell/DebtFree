import enum
from datetime import datetime, date
from sqlalchemy import String, Numeric, DateTime, Date, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionCategory(str, enum.Enum):
    # Required expenses
    RENT = "rent"
    MORTGAGE = "mortgage"
    UTILITIES = "utilities"
    GROCERIES = "groceries"
    GAS = "gas"
    INSURANCE = "insurance"
    MEDICAL = "medical"
    # Discretionary
    DINING = "dining"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    AMAZON = "amazon"
    SUBSCRIPTIONS = "subscriptions"
    CLOTHING = "clothing"
    TRAVEL = "travel"
    # Financial
    DEBT_PAYMENT = "debt_payment"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    # Other
    INCOME = "income"
    TRANSFER = "transfer"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    category: Mapped[TransactionCategory] = mapped_column(Enum(TransactionCategory), default=TransactionCategory.OTHER)
    description: Mapped[str] = mapped_column(String(500), default="")
    merchant: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_recurring: Mapped[bool] = mapped_column(default=False)
    is_essential: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="transactions")
