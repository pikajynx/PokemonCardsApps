"""Fanatics Collect via Apify Actor - resilient version"""
import os
import httpx
import asyncio

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "crawloop~fanatics-collect-scraper"


async def get_fanatics_listings(query: str) -> dict:
    results = {"sold": [], "auctions": [], "buy_now": []}
    if not API_KEY:
        return {"error": None, **results}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 20},
                json={"searchQuery": query, "maxItems": 10},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {"error": None, **results}
            items = resp.json()
            if not isinstance(items, list):
                return {"error": None, **results}
            for item in items[:10]:
                entry = {
                    "title": str(item.get("title", ""))[:100],
                    "price": "",
                    "grade": str(item.get("grade", "")),
                    "grader": str(item.get("gradingCompany", "")),
                    "bids": item.get("bidCount", ""),
                    "url": item.get("listingUrl", ""),
                    "close_date": item.get("closeDate", ""),
                }
                for k in ["realizedPrice", "currentBid", "startingBid"]:
                    v = item.get(k)
                    if v:
                        entry["price"] = f"${v}"
                        break
                if item.get("isSold"):
                    results["sold"].append(entry)
                else:
                    results["auctions"].append(entry)
    except Exception:
        return {"error": None, **results}
    return {"error": None, **results}
