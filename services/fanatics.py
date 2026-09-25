"""Fanatics Collect via Apify Actor (Algolia API-based, fast)"""
import os
import httpx

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "crawloop/fanatics-collect-scraper"


async def get_fanatics_listings(query: str) -> dict:
    """Get Fanatics Collect listings: sold, auctions, buy now."""
    results = {"sold": [], "auctions": [], "buy_now": []}

    if not API_KEY:
        return {"error": "Apify API key not configured", **results}

    async with httpx.AsyncClient(timeout=90) as client:
        try:
            # Use synchronous run endpoint
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 60},
                json={
                    "searchQuery": query,
                    "maxItems": 30,
                    "marketplace": "all",
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            items = resp.json()

            if not isinstance(items, list):
                return {"error": "Unexpected Fanatics response", **results}

            for item in items[:25]:
                entry = {
                    "title": item.get("title", item.get("subtitle", "")),
                    "price": _fmt_price(item),
                    "grade": item.get("grade", ""),
                    "grader": item.get("gradingCompany", ""),
                    "bids": item.get("bidCount", ""),
                    "url": item.get("listingUrl", ""),
                    "image": item.get("imageUrl", ""),
                    "close_date": item.get("closeDate", item.get("soldDate", "")),
                }

                status = item.get("status", "").lower()
                is_sold = item.get("isSold", False)

                if is_sold or "sold" in status:
                    results["sold"].append(entry)
                elif "buy" in status or "fixed" in status or "marketplace" in str(item.get("marketplace", "")).lower():
                    results["buy_now"].append(entry)
                else:
                    results["auctions"].append(entry)

        except httpx.HTTPStatusError as e:
            return {"error": f"Fanatics API error: {e.response.status_code}", **results}
        except Exception as e:
            return {"error": f"Fanatics: {str(e)[:100]}", **results}

    return {"error": None, **results}


def _fmt_price(item: dict) -> str:
    """Get the best available price from a Fanatics item."""
    for key in ["realizedPrice", "currentBid", "startingBid", "estimatedValue"]:
        val = item.get(key)
        if val and str(val).strip():
            return f"${val}"
    return ""
