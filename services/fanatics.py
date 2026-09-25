"""Fanatics Collect scraper using Playwright"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://www.fanaticscollect.com"


async def get_fanatics_listings(query: str) -> dict:
    """Scrape Fanatics Collect for sold items, auctions, and buy now listings."""
    results = {"sold": [], "auctions": [], "buy_now": []}

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = await browser.new_page()

            # Search on Fanatics Collect
            search_url = f"{BASE_URL}/search?q={query.replace(' ', '+')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            # Try to get sold items
            try:
                sold = await _extract_section(page, "sold", query)
                results["sold"] = sold[:10]
            except Exception:
                pass

            # Try to get buy now listings
            try:
                buy_now = await _extract_section(page, "buy_now", query)
                results["buy_now"] = buy_now[:10]
            except Exception:
                pass

            # Try to get auction listings
            try:
                auctions = await _extract_section(page, "auction", query)
                results["auctions"] = auctions[:10]
            except Exception:
                pass

        except Exception as e:
            return {"error": f"Fanatics: {str(e)}", **results}
        finally:
            if browser:
                await browser.close()

    return {"error": None, **results}


async def _extract_section(page, section_type: str, query: str) -> list:
    """Extract listings from a Fanatics search results page."""
    items = []

    # Fanatics uses React - wait for content to load
    await page.wait_for_timeout(2000)

    # Try multiple selector strategies
    # Card items are typically in a grid with price and title
    cards = await page.query_selector_all("[class*='card'], [class*='item'], [class*='listing'], [class*='product']")

    if not cards:
        # Try broader selectors
        cards = await page.query_selector_all("a[href*='/item/'], a[href*='/listing/'], a[href*='/product/']")

    for card in cards[:15]:
        try:
            title_el = await card.query_selector("[class*='title'], [class*='name'], h3, h4, p")
            price_el = await card.query_selector("[class*='price'], [class*='amount'], [class*='bid']")
            link_el = await card.query_selector("a[href]")

            title = await title_el.inner_text() if title_el else ""
            price = await price_el.inner_text() if price_el else ""
            link = await link_el.get_attribute("href") if link_el else ""

            if title and len(title.strip()) > 3:
                items.append({
                    "title": title.strip()[:120],
                    "price": _clean_price(price),
                    "url": f"{BASE_URL}{link}" if link and link.startswith("/") else link,
                    "type": section_type,
                })
        except Exception:
            continue

    return items


def _clean_price(price_str: str) -> str:
    """Extract numeric price from a string like '$45.00' or 'Sold for $45.00'."""
    import re
    if not price_str:
        return ""
    match = re.search(r'\$[\d,]+\.?\d*', price_str)
    return match.group(0) if match else price_str.strip()
