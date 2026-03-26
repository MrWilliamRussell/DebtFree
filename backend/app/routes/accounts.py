"""Account CRUD + Plaid bank connection routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.account import Account, AccountType
from app.models.connected_account import ConnectedAccount, ConnectionStatus
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.schemas import AccountOut, AccountCreate
from app.services import plaid_service
from app.services.nlp_parser import categorize_transaction

router = APIRouter()

ESSENTIAL_CATEGORIES = {
    TransactionCategory.RENT, TransactionCategory.MORTGAGE,
    TransactionCategory.UTILITIES, TransactionCategory.GROCERIES,
    TransactionCategory.GAS, TransactionCategory.INSURANCE,
    TransactionCategory.MEDICAL,
}


# ── Standard Account CRUD ──

@router.get("/", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.is_active == True))
    return result.scalars().all()


@router.post("/", response_model=AccountOut, status_code=201)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**data.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=AccountOut)
async def update_account(account_id: int, data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, val in data.model_dump().items():
        setattr(account, key, val)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    await db.commit()


# ── Plaid Bank Connection ──

@router.get("/plaid/status")
async def plaid_status():
    """Check if Plaid is configured."""
    return {"configured": plaid_service.is_configured()}


@router.post("/plaid/link-token")
async def create_link_token():
    """Get a Plaid Link token to start the bank connection flow.

    The frontend uses this token with the Plaid Link widget.
    The user logs into their bank through Plaid's secure portal.
    We NEVER see or store their bank password.
    """
    try:
        result = await plaid_service.create_link_token()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid error: {str(e)}")


@router.post("/plaid/exchange-token")
async def exchange_token(public_token: str, institution_name: str = "", db: AsyncSession = Depends(get_db)):
    """Exchange the public_token from Plaid Link for a permanent access_token.

    Called after user successfully authenticates with their bank.
    Creates a ConnectedAccount record and fetches account details.
    """
    try:
        token_data = await plaid_service.exchange_public_token(public_token)
        accounts = await plaid_service.get_accounts(token_data["access_token"])

        connected_accounts = []
        for acct in accounts:
            # Map Plaid account type to our AccountType
            acct_type = _map_plaid_account_type(acct["subtype"])

            # Create our local account
            local_account = Account(
                name=acct["name"] or acct["official_name"] or f"{institution_name} Account",
                account_type=acct_type,
                institution=institution_name,
                balance=acct["balance_current"],
                credit_limit=acct["balance_limit"],
            )
            db.add(local_account)
            await db.flush()

            # Create connected account record
            conn = ConnectedAccount(
                institution_name=institution_name,
                plaid_access_token=token_data["access_token"],
                plaid_item_id=token_data["item_id"],
                account_id_local=local_account.id,
                plaid_account_id=acct["account_id"],
                account_name=acct["name"] or "",
                account_mask=acct["mask"] or "",
                account_subtype=acct["subtype"],
                status=ConnectionStatus.ACTIVE,
            )
            db.add(conn)
            connected_accounts.append({
                "local_account_id": local_account.id,
                "name": acct["name"],
                "type": acct["subtype"],
                "mask": acct["mask"],
                "balance": acct["balance_current"],
            })

        await db.commit()
        return {"connected": len(connected_accounts), "accounts": connected_accounts}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.get("/plaid/connected")
async def list_connected_accounts(db: AsyncSession = Depends(get_db)):
    """List all connected bank/credit card accounts."""
    result = await db.execute(select(ConnectedAccount))
    conns = result.scalars().all()
    return [
        {
            "id": c.id,
            "institution": c.institution_name,
            "account_name": c.account_name,
            "mask": c.account_mask,
            "subtype": c.account_subtype,
            "status": c.status.value,
            "last_synced": c.last_synced.isoformat() if c.last_synced else None,
            "error": c.error_message,
            "local_account_id": c.account_id_local,
        }
        for c in conns
    ]


@router.post("/plaid/sync/{connected_account_id}")
async def sync_transactions(connected_account_id: int, db: AsyncSession = Depends(get_db)):
    """Pull new transactions from a connected bank account.

    Uses Plaid's incremental sync — only fetches new/modified transactions.
    Each transaction is auto-categorized via rules + LLM.
    """
    conn = await db.get(ConnectedAccount, connected_account_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connected account not found")

    try:
        sync_result = await plaid_service.sync_transactions(
            conn.plaid_access_token, conn.last_cursor
        )

        imported = 0
        llm_categorized = 0

        for txn_data in sync_result["transactions"]:
            if txn_data.get("pending"):
                continue

            # Plaid: positive amount = money leaving account (expense)
            amount = abs(txn_data["amount"])
            is_expense = txn_data["amount"] > 0
            txn_type = TransactionType.EXPENSE if is_expense else TransactionType.INCOME

            # Categorize: Plaid category → our category → LLM fallback
            category_str = plaid_service.map_plaid_category(txn_data.get("category", ""))
            try:
                category = TransactionCategory(category_str)
            except ValueError:
                category = TransactionCategory.OTHER

            # LLM fallback for uncategorized
            if category == TransactionCategory.OTHER:
                try:
                    llm_cat = await categorize_transaction(
                        txn_data["name"], txn_data.get("merchant_name", "")
                    )
                    category = TransactionCategory(llm_cat)
                    llm_categorized += 1
                except Exception:
                    pass

            txn = Transaction(
                account_id=conn.account_id_local,
                date=txn_data["date"],
                amount=amount,
                transaction_type=txn_type,
                category=category,
                description=txn_data["name"],
                merchant=txn_data.get("merchant_name", txn_data["name"])[:300],
                is_essential=category in ESSENTIAL_CATEGORIES,
            )
            db.add(txn)
            imported += 1

        # Update sync state
        conn.last_cursor = sync_result["next_cursor"]
        conn.last_synced = datetime.utcnow()
        conn.status = ConnectionStatus.ACTIVE
        conn.error_message = ""

        await db.commit()

        return {
            "imported": imported,
            "llm_categorized": llm_categorized,
            "removed": len(sync_result["removed_ids"]),
        }

    except Exception as e:
        conn.status = ConnectionStatus.ERROR
        conn.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/plaid/sync-all")
async def sync_all_accounts(db: AsyncSession = Depends(get_db)):
    """Sync all connected accounts at once."""
    result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.status == ConnectionStatus.ACTIVE)
    )
    conns = result.scalars().all()

    results = []
    for conn in conns:
        try:
            sync_result = await sync_transactions(conn.id, db)
            results.append({"account": conn.account_name, "status": "ok", **sync_result})
        except Exception as e:
            results.append({"account": conn.account_name, "status": "error", "error": str(e)})

    return {"synced": len(results), "results": results}


@router.delete("/plaid/connected/{connected_account_id}", status_code=204)
async def disconnect_account(connected_account_id: int, db: AsyncSession = Depends(get_db)):
    """Disconnect a linked bank account. Removes the Plaid token."""
    conn = await db.get(ConnectedAccount, connected_account_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connected account not found")
    conn.status = ConnectionStatus.DISCONNECTED
    conn.plaid_access_token = ""
    await db.commit()


def _map_plaid_account_type(subtype: str) -> AccountType:
    mapping = {
        "checking": AccountType.CHECKING,
        "savings": AccountType.SAVINGS,
        "credit card": AccountType.CREDIT_CARD,
        "mortgage": AccountType.LOAN,
        "student": AccountType.LOAN,
        "auto": AccountType.LOAN,
        "401k": AccountType.INVESTMENT,
        "ira": AccountType.INVESTMENT,
        "brokerage": AccountType.INVESTMENT,
    }
    return mapping.get(subtype, AccountType.CHECKING)
