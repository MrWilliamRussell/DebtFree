"""Background scheduler for automated financial data sync.

Runs as part of the FastAPI app (no separate process needed).
Uses APScheduler to handle:
- Plaid bank/credit card sync (every 6 hours by default)
- Amazon order scraping (daily)
- Discord coaching nudges (daily)
- Anomaly detection (after each sync)
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger("debtfree.scheduler")

scheduler = AsyncIOScheduler()


# ── Job: Sync all Plaid-connected accounts ──

async def job_sync_plaid_accounts():
    """Pull new transactions from all connected bank accounts."""
    from app.database import async_session
    from app.models.connected_account import ConnectedAccount, ConnectionStatus
    from app.services import plaid_service
    from app.services.nlp_parser import categorize_transaction
    from app.models.transaction import Transaction, TransactionType, TransactionCategory
    from sqlalchemy import select

    logger.info("Scheduler: Starting Plaid sync for all accounts")

    async with async_session() as db:
        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.status == ConnectionStatus.ACTIVE)
        )
        conns = result.scalars().all()

        for conn in conns:
            try:
                sync_result = await plaid_service.sync_transactions(
                    conn.plaid_access_token, conn.last_cursor
                )

                imported = 0
                for txn_data in sync_result["transactions"]:
                    if txn_data.get("pending"):
                        continue

                    amount = abs(txn_data["amount"])
                    is_expense = txn_data["amount"] > 0
                    txn_type = TransactionType.EXPENSE if is_expense else TransactionType.INCOME

                    category_str = plaid_service.map_plaid_category(txn_data.get("category", ""))
                    try:
                        category = TransactionCategory(category_str)
                    except ValueError:
                        category = TransactionCategory.OTHER

                    if category == TransactionCategory.OTHER:
                        try:
                            llm_cat = await categorize_transaction(
                                txn_data["name"], txn_data.get("merchant_name", "")
                            )
                            category = TransactionCategory(llm_cat)
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
                        is_essential=category in _ESSENTIAL,
                    )
                    db.add(txn)
                    imported += 1

                conn.last_cursor = sync_result["next_cursor"]
                conn.last_synced = datetime.utcnow()
                conn.status = ConnectionStatus.ACTIVE
                conn.error_message = ""
                await db.commit()

                if imported > 0:
                    logger.info(f"Scheduler: Synced {imported} transactions from {conn.institution_name}")

                    # Send Discord alert for new transactions
                    from app.services.discord_alerts import send_discord_alert
                    await send_discord_alert(
                        f"**Auto-Sync Complete** {conn.institution_name}: {imported} new transactions imported"
                    )

            except Exception as e:
                logger.error(f"Scheduler: Failed to sync {conn.institution_name}: {e}")
                conn.status = ConnectionStatus.ERROR
                conn.error_message = str(e)
                await db.commit()


# ── Job: Scrape Amazon orders ──

async def job_scrape_amazon():
    """Automatically pull Amazon order history using stored credentials."""
    from app.database import async_session
    from app.services.credential_vault import StoredCredential, CredentialType, decrypt_credentials
    from app.services.amazon_scraper import scrape_amazon_orders
    from app.models.transaction import Transaction, TransactionType
    from app.models.account import Account, AccountType
    from sqlalchemy import select

    logger.info("Scheduler: Starting Amazon order scrape")

    async with async_session() as db:
        # Find Amazon credentials
        result = await db.execute(
            select(StoredCredential).where(
                StoredCredential.credential_type == CredentialType.AMAZON,
                StoredCredential.is_active == True,
            )
        )
        cred = result.scalar_one_or_none()
        if not cred:
            logger.info("Scheduler: No Amazon credentials stored, skipping")
            return

        try:
            creds = decrypt_credentials(cred.encrypted_data)
            orders = await scrape_amazon_orders(
                email=creds["email"],
                password=creds["password"],
                months_back=1,  # Only last month for scheduled runs
            )

            if not orders:
                logger.info("Scheduler: No new Amazon orders found")
                return

            # Find or create an Amazon account
            acct_result = await db.execute(
                select(Account).where(Account.name.ilike("%amazon%"))
            )
            account = acct_result.scalar_one_or_none()
            if not account:
                account = Account(
                    name="Amazon",
                    account_type=AccountType.CASH,
                    institution="Amazon",
                )
                db.add(account)
                await db.flush()

            imported = 0
            for order in orders:
                # Check for duplicate by order_id in description
                existing = await db.execute(
                    select(Transaction).where(
                        Transaction.description.contains(order.order_id)
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                txn = Transaction(
                    account_id=account.id,
                    date=order.date,
                    amount=order.amount,
                    transaction_type=TransactionType.EXPENSE,
                    category=order.category,
                    description=f"{order.title} (Order: {order.order_id})",
                    merchant="Amazon",
                    is_essential=order.category in _ESSENTIAL,
                    is_recurring=order.is_subscription,
                )
                db.add(txn)
                imported += 1

            cred.last_used = datetime.utcnow()
            cred.last_error = ""
            await db.commit()

            if imported > 0:
                logger.info(f"Scheduler: Imported {imported} Amazon orders")
                from app.services.discord_alerts import send_discord_alert
                await send_discord_alert(
                    f"**Amazon Auto-Import** {imported} new orders imported"
                )

        except Exception as e:
            logger.error(f"Scheduler: Amazon scrape failed: {e}")
            cred.last_error = str(e)
            cred.last_used = datetime.utcnow()
            await db.commit()


# ── Job: Daily coaching nudge ──

async def job_daily_nudge():
    """Send a daily coaching message to Discord."""
    if not settings.discord_webhook_url:
        return

    from app.database import async_session
    from app.models.transaction import Transaction, TransactionType
    from app.models.debt import Debt
    from app.models.income import Income
    from app.services.coaching import generate_daily_nudge
    from app.services.discord_alerts import send_discord_alert
    from app.routes.dashboard import monthly_income_amount
    from sqlalchemy import select, and_
    from datetime import date

    async with async_session() as db:
        today = date.today()
        month_start = today.replace(day=1)

        incomes_result = await db.execute(select(Income).where(Income.is_active == True))
        incomes = incomes_result.scalars().all()
        monthly_income = sum(monthly_income_amount(i) for i in incomes)

        expenses_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.date >= month_start,
                )
            )
        )
        monthly_expenses = sum(float(t.amount) for t in expenses_result.scalars().all())

        debts_result = await db.execute(select(Debt).where(Debt.is_active == True))
        total_debt = sum(float(d.current_balance) for d in debts_result.scalars().all())

        message = await generate_daily_nudge(
            health_score=65,
            net_monthly=monthly_income - monthly_expenses,
            days_on_budget=today.day,
            total_debt=total_debt,
            debt_change_7d=0,
        )

        await send_discord_alert(f"**Daily Coach** {message}")


# ── Essential categories for reference ──

from app.models.transaction import TransactionCategory

_ESSENTIAL = {
    TransactionCategory.RENT, TransactionCategory.MORTGAGE,
    TransactionCategory.UTILITIES, TransactionCategory.GROCERIES,
    TransactionCategory.GAS, TransactionCategory.INSURANCE,
    TransactionCategory.MEDICAL,
}


# ── Scheduler Setup ──

def setup_scheduler():
    """Configure and start all scheduled jobs."""

    # Plaid sync: every 6 hours
    scheduler.add_job(
        job_sync_plaid_accounts,
        IntervalTrigger(hours=6),
        id="plaid_sync",
        name="Sync Plaid bank accounts",
        replace_existing=True,
    )

    # Amazon scrape: daily at 6 AM
    scheduler.add_job(
        job_scrape_amazon,
        CronTrigger(hour=6, minute=0),
        id="amazon_scrape",
        name="Scrape Amazon orders",
        replace_existing=True,
    )

    # Daily coaching nudge: 8 AM
    scheduler.add_job(
        job_daily_nudge,
        CronTrigger(hour=8, minute=0),
        id="daily_nudge",
        name="Daily coaching nudge",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started: Plaid (6h), Amazon (daily 6AM), Coach (daily 8AM)")


def get_scheduler_status() -> list[dict]:
    """Get status of all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs
