"""Encrypted credential vault for storing service credentials.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The encryption key is derived from SECRET_KEY in .env.
Credentials are encrypted at rest in PostgreSQL — never stored plaintext.

IMPORTANT: This is self-hosted, privacy-first by design.
All credentials stay on YOUR machine in YOUR database, encrypted.
"""

import base64
import hashlib
import json
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import String, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base
from app.config import settings


class CredentialType(str, enum.Enum):
    AMAZON = "amazon"
    BANK_DIRECT = "bank_direct"  # For banks without Plaid support
    EMAIL = "email"  # For receipt scanning
    CUSTOM = "custom"


class StoredCredential(Base):
    __tablename__ = "stored_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))  # "Amazon", "Chase Direct", etc.
    credential_type: Mapped[CredentialType] = mapped_column(Enum(CredentialType))
    encrypted_data: Mapped[str] = mapped_column(Text)  # Fernet-encrypted JSON blob
    is_active: Mapped[bool] = mapped_column(default=True)
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the app's SECRET_KEY."""
    if settings.secret_key == "change-me-in-production":
        raise ValueError("Default secret key is being used. Please change it in production.")
    
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_credentials(data: dict) -> str:
    """Encrypt a dict of credentials (e.g. {"email": "x", "password": "y"}).

    Returns a Fernet-encrypted string safe for database storage.
    """
    f = _get_fernet()
    json_bytes = json.dumps(data).encode("utf-8")
    return f.encrypt(json_bytes).decode("utf-8")


def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt stored credentials back to a dict.

    Raises cryptography.fernet.InvalidToken if the SECRET_KEY changed.
    """
    f = _get_fernet()
    json_bytes = f.decrypt(encrypted.encode("utf-8"))
    return json.loads(json_bytes.decode("utf-8"))


def mask_credentials(data: dict) -> dict:
    """Return a masked version for display (never show full passwords)."""
    masked = {}
    for key, value in data.items():
        if key in ("password", "secret", "token", "api_key"):
            masked[key] = value[:2] + "****" + value[-2:] if len(value) > 4 else "****"
        elif key in ("email", "username"):
            parts = value.split("@")
            if len(parts) == 2:
                masked[key] = parts[0][:2] + "****@" + parts[1]
    return masked