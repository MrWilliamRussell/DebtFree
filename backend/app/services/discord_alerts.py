"""Discord webhook integration for budget alerts."""

import aiohttp
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract

from app.config import settings
from app.models.transaction import Transaction, TransactionType
from app.models.budget import Budget
import logging

logger = logging.getLogger(__name__)

async def send_discord_alert(message: str):
    """Send a message to the configured Discord webhook with retry and error handling."""
    if not settings.discord_webhook_url:
        return

    payload = {"content": message}
    retries = 3
    backoff_time = 1  # seconds

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.discord_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:
                        return
                    else:
                        logger.error(f"Failed to send Discord alert. Status code: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"Client error occurred while sending Discord alert: {e}")
        except asyncio.TimeoutError:
            logger.error("Timeout occurred while sending Discord alert")

        if attempt < retries - 1:
            await asyncio.sleep(backoff_time)
            backoff_time *= 2

    logger.error("Failed to send Discord alert after multiple attempts")


async def check_budget_and_alert(db: AsyncSession, transaction: Transaction):
    """After a new transaction, check if any budget threshold is exceeded."""
    if transaction.transaction_type != TransactionType.EXPENSE:
        return

    today = date.today()

    # Find matching budget for this category
    budget_result = await db.execute(
        select(Budget).where(
            and_(
                Budget.category == transaction.category,
                Budget.is_active == True,
            )
        )
    )
    budget = budget_result.scalar_one_or_none()
    if not budget:
        return

    # Sum expenses this month in this category
    month_start = today.replace(day=1)
    spent_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.category == transaction.category,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= month_start,
                Transaction.date <= today,
            )
        )
    )
    total_spent = float(spent_result.scalar() or 0)
    limit = float(budget.monthly_limit)
    threshold = float(budget.alert_threshold)

    if total_spent >= limit:
        await send_discord_alert(
            f"**BUDGET EXCEEDED** {transaction.category.value}: "
            f"${total_spent:.2f} / ${limit:.2f} "
            f"(Latest: {transaction.description} ${float(transaction.amount):.2f})"
        )
    elif total_spent >= limit * threshold:
        pct = total_spent / limit * 100
        await send_discord_alert(
            f"**Budget Warning** {transaction.category.value}: "
            f"${total_spent:.2f} / ${limit:.2f} ({pct:.0f}%) "
            f"(Latest: {transaction.description} ${float(transaction.amount):.2f})"
        )