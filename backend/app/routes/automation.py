"""Automation routes — credential management, sync scheduling, manual triggers."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.credential_vault import (
    StoredCredential, CredentialType,
    encrypt_credentials, decrypt_credentials, mask_credentials,
)
from app.services.scheduler import (
    scheduler, get_scheduler_status,
    job_sync_plaid_accounts, job_scrape_amazon, job_daily_nudge,
)

router = APIRouter()


# ── Schemas ──

class CredentialStore(BaseModel):
    name: str
    credential_type: str  # "amazon", "bank_direct", "email", "custom"
    credentials: dict  # {"email": "x", "password": "y"} — encrypted before storage


class CredentialOut(BaseModel):
    id: int
    name: str
    credential_type: str
    masked_credentials: dict
    is_active: bool
    last_used: Optional[str] = None
    last_error: str = ""
    created_at: str


class SyncScheduleUpdate(BaseModel):
    plaid_interval_hours: int = 6
    amazon_enabled: bool = True
    amazon_hour: int = 6
    nudge_enabled: bool = True
    nudge_hour: int = 8


# ── Credential Management ──

@router.post("/credentials", status_code=201)
async def store_credentials(data: CredentialStore, db: AsyncSession = Depends(get_db)):
    """Store encrypted credentials for automated syncing.

    Credentials are encrypted with AES-128 (Fernet) before storage.
    The encryption key is derived from SECRET_KEY in .env.
    """
    try:
        cred_type = CredentialType(data.credential_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid type. Use: {[t.value for t in CredentialType]}")

    encrypted = encrypt_credentials(data.credentials)

    cred = StoredCredential(
        name=data.name,
        credential_type=cred_type,
        encrypted_data=encrypted,
        is_active=True,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)

    return {
        "id": cred.id,
        "name": cred.name,
        "type": cred.credential_type.value,
        "message": "Credentials stored (encrypted). Never stored in plaintext.",
    }


@router.get("/credentials")
async def list_credentials(db: AsyncSession = Depends(get_db)):
    """List stored credentials (masked — passwords never returned)."""
    result = await db.execute(select(StoredCredential))
    creds = result.scalars().all()

    out = []
    for c in creds:
        try:
            decrypted = decrypt_credentials(c.encrypted_data)
            masked = mask_credentials(decrypted)
        except Exception:
            masked = {"error": "Could not decrypt — SECRET_KEY may have changed"}

        out.append(CredentialOut(
            id=c.id,
            name=c.name,
            credential_type=c.credential_type.value,
            masked_credentials=masked,
            is_active=c.is_active,
            last_used=c.last_used.isoformat() if c.last_used else None,
            last_error=c.last_error,
            created_at=c.created_at.isoformat(),
        ))
    return out


@router.delete("/credentials/{cred_id}", status_code=204)
async def delete_credentials(cred_id: int, db: AsyncSession = Depends(get_db)):
    """Delete stored credentials (removes encrypted data permanently)."""
    cred = await db.get(StoredCredential, cred_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.delete(cred)
    await db.commit()


@router.post("/credentials/{cred_id}/test")
async def test_credentials(cred_id: int, db: AsyncSession = Depends(get_db)):
    """Test stored credentials by attempting a login."""
    cred = await db.get(StoredCredential, cred_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    try:
        data = decrypt_credentials(cred.encrypted_data)
    except Exception:
        raise HTTPException(status_code=500, detail="Decryption failed — check SECRET_KEY")

    if cred.credential_type == CredentialType.AMAZON:
        try:
            from app.services.amazon_scraper import scrape_amazon_orders
            orders = await scrape_amazon_orders(
                email=data["email"],
                password=data["password"],
                months_back=1,
            )
            cred.last_used = datetime.utcnow()
            cred.last_error = ""
            await db.commit()
            return {"status": "ok", "orders_found": len(orders)}
        except Exception as e:
            cred.last_error = str(e)
            await db.commit()
            return {"status": "error", "detail": str(e)}

    return {"status": "ok", "detail": "Credential decrypts successfully"}


# ── Scheduler Control ──

@router.get("/scheduler/status")
async def scheduler_status():
    """Get status of all automated sync jobs."""
    return {
        "running": scheduler.running,
        "jobs": get_scheduler_status(),
    }


@router.post("/scheduler/trigger/{job_id}")
async def trigger_job(job_id: str):
    """Manually trigger a scheduled job right now."""
    job_map = {
        "plaid_sync": job_sync_plaid_accounts,
        "amazon_scrape": job_scrape_amazon,
        "daily_nudge": job_daily_nudge,
    }
    job_fn = job_map.get(job_id)
    if not job_fn:
        raise HTTPException(status_code=404, detail=f"Job not found. Available: {list(job_map.keys())}")

    try:
        await job_fn()
        return {"status": "ok", "job": job_id, "message": "Job executed successfully"}
    except Exception as e:
        return {"status": "error", "job": job_id, "detail": str(e)}


@router.post("/sync-now")
async def sync_everything():
    """Trigger all syncs right now (Plaid + Amazon)."""
    results = {}

    try:
        await job_sync_plaid_accounts()
        results["plaid"] = "ok"
    except Exception as e:
        results["plaid"] = f"error: {str(e)}"

    try:
        await job_scrape_amazon()
        results["amazon"] = "ok"
    except Exception as e:
        results["amazon"] = f"error: {str(e)}"

    return {"results": results}
