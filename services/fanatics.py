"""Fanatics Collect via Apify"""
import os
import httpx
import asyncio

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTORS = [
    "jungle_synthesizer~fanaticscollect-weekly-auction-scraper",
    "lulzasaur~fanaticscollect-scraper",
]


async def _try_actor(client, actor_id: str, query: str, mode: str) -> list:
    try:
        resp = await client.post(
            f"https://api.apify.com/v2/actors/{actor_id}/run-sync-get-dataset-items",
            params={"token": API_KEY, "timeout": 20},
            json={
                "keyword": query,
                "searchQuery": query,
                "maxItems": 10,
                "mode": mode,
                "sp_intended_usage": "Card price research",
                "sp_improvement_suggestions": "",
                "sp_contact": "",
                "categories": [],
                "graders": [],
            },
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            return []
        items = resp.json()
        if not isinstance(items, list) or not items:
            return []
        results = []
        for item in items[:10]:
            entry = {
                "title": str(item.get("title", ""))[:120],
                "price": "",
                "grade": str(item.get("grade", item.get("gradingCompany", ""))),
                "bids": item.get("bidCount", item.get("bid_count", "")),
                "url": item.get("url", item.get("listingUrl", "")),
                "close_date": item.get("closeDate", item.get("soldDate", "")),
            }
            for k in ["soldPrice", "realizedPrice", "hammerPrice", "currentBid", "price", "startingBid"]:
                v = item.get(k)
                if v and str(v).strip():
                    entry["price"] = f"${v}"
                    break
            results.append(entry)
        return results
    except Exception:
        return []


async def get_fanatics_listings(query: str) -> dict:
    results = {"sold": [], "auctions": [], "buy_now": []}
    if not API_KEY:
        return {"error": None, **results}

    async with httpx.AsyncClient(timeout=45) as client:
        for actor_id in ACTORS:
            for mode in ["weekly_auction", "sold", "buy_now"]:
                data = await _try_actor(client, actor_id, query, mode)
                if data:
                    if mode == "sold":
                        results["sold"] = data
                    elif mode == "buy_now":
                        results["buy_now"] = data
                    else:
                        results["auctions"] = data
        if any(results.values()):
            return {"error": None, **results}

    return {"error": None, **results}
