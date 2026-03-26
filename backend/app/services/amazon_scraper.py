"""Amazon order history scraper using headless browser (Playwright).

Automates login + order history extraction so the user doesn't need
to manually export CSVs. Credentials are pulled from the encrypted vault.

IMPORTANT: This is for PERSONAL use on YOUR OWN Amazon account.
Browser automation may be against Amazon's ToS — use at your own discretion.
This runs locally in your Docker container and never sends data externally.

Falls back gracefully if Amazon blocks or changes their UI.
"""

import asyncio
import re
from datetime import date, datetime
from dataclasses import dataclass

from app.models.transaction import TransactionType, TransactionCategory
from app.services.amazon_importer import categorize_amazon_item, ESSENTIAL_CATEGORIES


@dataclass
class AmazonOrder:
    date: date
    amount: float
    title: str
    order_id: str
    category: TransactionCategory = TransactionCategory.AMAZON
    is_subscription: bool = False


async def scrape_amazon_orders(
    email: str,
    password: str,
    months_back: int = 3,
    headless: bool = True,
) -> list[AmazonOrder]:
    """Log into Amazon and scrape order history.

    Args:
        email: Amazon account email (from encrypted vault)
        password: Amazon account password (from encrypted vault)
        months_back: How many months of history to pull
        headless: Run browser invisibly (True) or visible for debugging (False)

    Returns:
        List of AmazonOrder objects ready for database insertion.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )

    orders = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            # Step 1: Navigate to Amazon sign-in
            await page.goto("https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2Fyour-orders%2Forders&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0", timeout=30000)

            # Step 2: Enter email
            await page.fill("#ap_email", email, timeout=10000)
            await page.click("#continue")
            await page.wait_for_timeout(2000)

            # Step 3: Enter password
            await page.fill("#ap_password", password, timeout=10000)
            await page.click("#signInSubmit")
            await page.wait_for_timeout(3000)

            # Check for CAPTCHA or 2FA
            if "ap/challenge" in page.url or "ap/mfa" in page.url:
                raise RuntimeError(
                    "Amazon requires CAPTCHA or 2FA verification. "
                    "Log in manually once to trust this device, then retry."
                )

            # Step 4: Navigate to order history
            current_year = datetime.now().year
            years_to_check = set()
            for m in range(months_back):
                check_date = datetime.now().replace(day=1)
                for _ in range(m):
                    check_date = check_date.replace(day=1)
                    if check_date.month == 1:
                        check_date = check_date.replace(year=check_date.year - 1, month=12)
                    else:
                        check_date = check_date.replace(month=check_date.month - 1)
                years_to_check.add(check_date.year)

            for year in sorted(years_to_check, reverse=True):
                await page.goto(
                    f"https://www.amazon.com/your-orders/orders?timeFilter=year-{year}",
                    timeout=30000,
                )
                await page.wait_for_timeout(2000)

                # Parse order cards
                page_orders = await _extract_orders_from_page(page, year)
                orders.extend(page_orders)

                # Check for pagination
                while True:
                    next_btn = await page.query_selector('a[aria-label="Next page"]')
                    if not next_btn:
                        break
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                    page_orders = await _extract_orders_from_page(page, year)
                    orders.extend(page_orders)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Amazon scrape failed: {str(e)}")
        finally:
            await browser.close()

    # Categorize each order
    for order in orders:
        order.category = categorize_amazon_item(order.title)
        order.is_subscription = any(
            kw in order.title.lower()
            for kw in ("subscribe", "prime", "audible", "kindle unlimited")
        )

    return orders


async def _extract_orders_from_page(page, year: int) -> list[AmazonOrder]:
    """Extract order data from the current orders page."""
    orders = []

    # Amazon uses .order-card or .order class for each order
    order_cards = await page.query_selector_all('.order-card, .a-box-group.order')

    for card in order_cards:
        try:
            # Extract date
            date_el = await card.query_selector('.order-info .a-color-secondary, .value[data-testid="order-date"]')
            date_text = await date_el.inner_text() if date_el else ""
            order_date = _parse_amazon_date(date_text, year)

            # Extract total
            total_el = await card.query_selector('.order-info .a-color-secondary + .a-color-secondary, .value[data-testid="order-total"]')
            total_text = await total_el.inner_text() if total_el else ""
            amount = _parse_amount(total_text)

            # Extract order ID
            order_id_el = await card.query_selector('.order-info .a-color-secondary:last-child, [data-testid="order-id"]')
            order_id = await order_id_el.inner_text() if order_id_el else ""
            order_id = order_id.replace("Order #", "").replace("Order#", "").strip()

            # Extract item titles
            title_els = await card.query_selector_all('.a-link-normal[href*="/dp/"], .yohtmlc-product-title')
            titles = []
            for t in title_els:
                text = await t.inner_text()
                if text.strip():
                    titles.append(text.strip()[:200])
            title = " | ".join(titles) if titles else "Amazon Purchase"

            if amount > 0 and order_date:
                orders.append(AmazonOrder(
                    date=order_date,
                    amount=amount,
                    title=title,
                    order_id=order_id,
                ))
        except Exception:
            continue

    return orders


def _parse_amazon_date(text: str, fallback_year: int) -> date | None:
    """Parse Amazon's date formats: 'March 15, 2026', 'Ordered on March 15, 2026', etc."""
    text = text.replace("Ordered on", "").replace("Order placed", "").strip()
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    match = re.search(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})?', text)
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else fallback_year
        month = months.get(month_name)
        if month:
            return date(year, month, day)
    return None


def _parse_amount(text: str) -> float:
    """Parse '$45.99' or 'USD 45.99' etc."""
    cleaned = re.sub(r'[^\d.]', '', text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
