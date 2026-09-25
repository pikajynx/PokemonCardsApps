"""Fanatics Collect scraper using httpx + BeautifulSoup"""
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.fanaticscollect.com"


async def get_fanatics_listings(query: str) -> dict:
    """Scrape Fanatics Collect for sold, auctions, and buy now listings."""
    results = {"sold": [], "auctions": [], "buy_now": []}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        try:
            # Search Fanatics Collect
            search_url = f"{BASE_URL}/search?q={query.replace(' ', '+')}"
            resp = await client.get(search_url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to extract listing cards
            # Fanatics uses React so HTML may be minimal - try common selectors
            cards = soup.select("[class*=card], [class*=item], [class*=listing], [class*=product], [class*=result]")

            for card in cards[:20]:
                title_el = card.select_one("[class*=title], [class*=name], h3, h4, p, a")
                price_el = card.select_one("[class*=price], [class*=amount], [class*=bid]")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else ""
                price = price_el.get_text(strip=True) if price_el else ""
                link = link_el.get("href", "") if link_el else ""

                if title and len(title) > 3:
                    entry = {
                        "title": title[:120],
                        "price": _clean_price(price),
                        "url": f"{BASE_URL}{link}" if link.startswith("/") else link,
                    }
                    results["sold"].append(entry)

            # If no cards found via HTML, try to get data from any structured content
            if not results["sold"]:
                # Try getting any text content that looks like listings
                all_text = soup.get_text(separator="\n", strip=True)
                if "no results" in all_text.lower() or len(all_text) < 100:
                    results["sold"] = []

        except httpx.HTTPStatusError as e:
            return {"error": f"Fanatics: HTTP {e.response.status_code}", **results}
        except Exception as e:
            return {"error": f"Fanatics: {str(e)[:100]}", **results}

    return {"error": None, **results}


def _clean_price(price_str: str) -> str:
    """Extract numeric price from a string."""
    import re
    if not price_str:
        return ""
    match = re.search(r"\$[\d,]+\.?\d*", price_str)
    return match.group(0) if match else price_str.strip()
