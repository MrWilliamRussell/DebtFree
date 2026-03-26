"""Plaid integration for secure bank/credit card transaction syncing.

Uses token-based OAuth — we NEVER store bank login credentials.
The user authenticates through Plaid Link (bank's own secure portal).
We receive a secure access token that can only pull transaction data.

Setup:
1. Sign up at https://dashboard.plaid.com/ (free dev account)
2. Get client_id and secret
3. Add to .env: PLAID_CLIENT_ID and PLAID_SECRET
4. Start in sandbox mode (PLAID_ENV=sandbox) for testing
"""

from datetime import date, timedelta, datetime
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.accounts_get_request import AccountsGetRequest

from app.config import settings


def _get_client() -> plaid_api.PlaidApi:
    """Create a Plaid API client."""
    config = plaid.Configuration(
        host={
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production,
        }.get(settings.plaid_env, plaid.Environment.Sandbox),
        api_key={
            "clientId": settings.plaid_client_id,
            "secret": settings.plaid_secret,
        },
    )
    api_client = plaid.ApiClient(config)
    return plaid_api.PlaidApi(api_client)


def is_configured() -> bool:
    """Check if Plaid credentials are set."""
    return bool(settings.plaid_client_id and settings.plaid_secret)


async def create_link_token(user_id: str = "default_user") -> dict:
    """Create a Plaid Link token for the frontend widget.

    The user clicks this to securely log into their bank — we never see the password.
    Returns a link_token to pass to the Plaid Link frontend component.
    """
    if not is_configured():
        raise ValueError("Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env")

    client = _get_client()
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name="DebtFree Dashboard",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    response = client.link_token_create(request)
    return {
        "link_token": response.link_token,
        "expiration": response.expiration,
    }


async def exchange_public_token(public_token: str) -> dict:
    """Exchange a public_token from Plaid Link for a permanent access_token.

    Called after the user successfully logs in via Plaid Link.
    The access_token is what we store (securely) to pull transactions.
    """
    client = _get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return {
        "access_token": response.access_token,
        "item_id": response.item_id,
    }


async def get_accounts(access_token: str) -> list[dict]:
    """Get all accounts linked to this access token."""
    client = _get_client()
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    return [
        {
            "account_id": a.account_id,
            "name": a.name,
            "official_name": a.official_name,
            "type": a.type.value if a.type else "",
            "subtype": a.subtype.value if a.subtype else "",
            "mask": a.mask or "",
            "balance_current": float(a.balances.current) if a.balances.current else 0,
            "balance_available": float(a.balances.available) if a.balances.available else 0,
            "balance_limit": float(a.balances.limit) if a.balances.limit else None,
        }
        for a in response.accounts
    ]


async def sync_transactions(access_token: str, cursor: str = "") -> dict:
    """Pull new transactions using Plaid's transaction sync API.

    Uses cursor-based incremental sync — only pulls new/modified transactions
    since the last sync, not the entire history every time.

    Returns:
        added: list of new transactions
        modified: list of updated transactions
        removed: list of removed transaction IDs
        next_cursor: cursor to use for next sync
        has_more: whether there are more pages
    """
    client = _get_client()
    all_added = []
    all_modified = []
    all_removed = []
    has_more = True
    next_cursor = cursor

    while has_more:
        request = TransactionsSyncRequest(
            access_token=access_token,
            cursor=next_cursor,
        )
        response = client.transactions_sync(request)

        all_added.extend(response.added)
        all_modified.extend(response.modified)
        all_removed.extend(response.removed)
        next_cursor = response.next_cursor
        has_more = response.has_more

    # Convert to plain dicts
    transactions = []
    for txn in all_added + all_modified:
        transactions.append({
            "plaid_transaction_id": txn.transaction_id,
            "plaid_account_id": txn.account_id,
            "date": txn.date.isoformat() if isinstance(txn.date, date) else str(txn.date),
            "amount": float(txn.amount),  # Plaid: positive = money out (expense)
            "name": txn.name or "",
            "merchant_name": txn.merchant_name or txn.name or "",
            "category": txn.personal_finance_category.primary if txn.personal_finance_category else "",
            "category_detailed": txn.personal_finance_category.detailed if txn.personal_finance_category else "",
            "pending": txn.pending,
            "iso_currency_code": txn.iso_currency_code or "USD",
        })

    removed_ids = [r.transaction_id for r in all_removed]

    return {
        "transactions": transactions,
        "removed_ids": removed_ids,
        "next_cursor": next_cursor,
        "count": len(transactions),
    }


# ── Plaid category → our category mapping ──
PLAID_CATEGORY_MAP = {
    "FOOD_AND_DRINK": "dining",
    "GROCERIES": "groceries",
    "GENERAL_MERCHANDISE": "shopping",
    "ENTERTAINMENT": "entertainment",
    "TRANSPORTATION": "gas",
    "GAS_STATIONS": "gas",
    "RENT": "rent",
    "MORTGAGE": "mortgage",
    "UTILITIES": "utilities",
    "INSURANCE": "insurance",
    "MEDICAL": "medical",
    "CLOTHING": "clothing",
    "TRAVEL": "travel",
    "SUBSCRIPTIONS": "subscriptions",
    "TRANSFER": "transfer",
    "INCOME": "income",
    "LOAN_PAYMENTS": "debt_payment",
    "INVESTMENTS": "investment",
}


def map_plaid_category(plaid_category: str) -> str:
    """Map Plaid's category to our TransactionCategory enum value."""
    if not plaid_category:
        return "other"
    upper = plaid_category.upper().replace(" ", "_")
    # Check direct match
    if upper in PLAID_CATEGORY_MAP:
        return PLAID_CATEGORY_MAP[upper]
    # Check partial match
    for key, val in PLAID_CATEGORY_MAP.items():
        if key in upper:
            return val
    return "other"
