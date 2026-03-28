import logging
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
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError

logger = logging.getLogger(__name__)

def _get_client() -> plaid_api.PlaidApi:
    """Create a Plaid API client."""
    logger.info("Creating Plaid API client")
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
    logger.info("Checking if Plaid is configured")
    return bool(settings.plaid_client_id and settings.plaid_secret)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def create_link_token(user_id: str = "default_user") -> dict:
    """Create a Plaid Link token for the frontend widget.

    The user clicks this to securely log into their bank — we never see the password.
    Returns a link_token to pass to the Plaid Link frontend component.
    """
    if not is_configured():
        logger.error("Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env")
        raise ValueError("Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env")

    client = _get_client()
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name="DebtFree Dashboard",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    logger.info("Starting API call to create link token")
    try:
        response = client.link_token_create(request)
        logger.info("API call to create link token successful")
        return {
            "link_token": response.link_token,
            "expiration": response.expiration,
        }
    except Exception as e:
        logger.error(f"API call to create link token failed: {e}")
        raise


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def exchange_public_token(public_token: str) -> dict:
    """Exchange a public_token from Plaid Link for a permanent access_token.

    Called after the user successfully logs in via Plaid Link.
    The access_token is what we store (securely) to pull transactions.
    """
    client = _get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    logger.info("Starting API call to exchange public token")
    try:
        response = client.item_public_token_exchange(request)
        logger.info("API call to exchange public token successful")
        return {
            "access_token": response.access_token,
            "item_id": response.item_id,
        }
    except Exception as e:
        logger.error(f"API call to exchange public token failed: {e}")
        raise