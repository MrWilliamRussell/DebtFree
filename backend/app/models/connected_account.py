"""Connected bank/credit card accounts via Plaid.

Stores Plaid access tokens (encrypted), NOT raw bank credentials.
The user authenticates through Plaid Link (bank's own OAuth portal).
We never see or store the user's bank password.
"""

import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConnectionStatus(str, enum.Enum):
    ACTIVE = "active"
    ERROR = "error"
    PENDING = "pending"
    DISCONNECTED = "disconnected"


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_name: Mapped[str] = mapped_column(String(200))
    institution_id: Mapped[str] = mapped_column(String(100), default="")
    plaid_access_token: Mapped[str] = mapped_column(Text)  # Encrypted in production
    plaid_item_id: Mapped[str] = mapped_column(String(200), unique=True)
    account_id_local: Mapped[int] = mapped_column(Integer, nullable=True)  # FK to our accounts table
    plaid_account_id: Mapped[str] = mapped_column(String(200), default="")
    account_name: Mapped[str] = mapped_column(String(200), default="")
    account_mask: Mapped[str] = mapped_column(String(10), default="")  # Last 4 digits
    account_subtype: Mapped[str] = mapped_column(String(50), default="")  # checking, credit card, etc.
    status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus), default=ConnectionStatus.PENDING)
    last_synced: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_cursor: Mapped[str] = mapped_column(Text, default="")  # Plaid sync cursor for incremental pulls
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
