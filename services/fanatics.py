"""Fanatics Collect via Apify Actor"""
import os
import httpx

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "crawloop/fanatics-collect-scraper"


async def get_fanatics_listings(query: str) -> dict:
    """Get Fanatics Collect listings."""
    results = {"sold": [], "auctions": [], "buy_now": []}

    if not API_KEY:
        return {"error": "Apify API key not configured", **results}

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 30},
                json={
                    "searchQuery": query,
                    "maxItems": 15,
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {"error": f"Fanatics: HTTP {resp.status_code}", **results}

            items = resp.json()
            if not isinstance(items, list):
                return {"error": None, **results}

            for item in items[:15]:
                entry = {
                    "title": str(item.get("title", ""))[:120],
                    "price": _fmt_price(item),
                    "grade": str(item.get("grade", "")),
                    "grader": str(item.get("gradingCompany", "")),
                    "bids": item.get("bidCount", ""),
                    "url": item.get("listingUrl", ""),
                    "close_date": item.get("closeDate", ""),
                }
                is_sold = item.get("isSold", False)
                status = str(item.get("status", "")).lower()
                if is_sold or "sold" in status:
                    results["sold"].append(entry)
                else:
                    results["auctions"].append(entry)

    except httpx.TimeoutException:
        return {"error": "Fanatics timed out (try again)", **results}
    except Exception as e:
        return {"error": f"Fanatics: {str(e)[:80]}", **results}

    return {"error": None, **results}


def _fmt_price(item: dict) -> str:
    for key in ["realizedPrice", "currentBid", "startingBid", "estimatedValue"]:
        val = item.get(key)
        if val and str(val).strip():
            return f"${val}"
    return ""
