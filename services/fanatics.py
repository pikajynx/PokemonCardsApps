"""Fanatics Collect via Apify Actor - jungle_synthesizer"""
import os
import httpx
import asyncio

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "jungle_synthesizer~fanaticscollect-weekly-auction-scraper"


async def _fetch_mode(client, query: str, mode: str, timeout: int = 25):
    """Fetch one mode (weekly_auction, sold, buy_now) from Fanatics."""
    try:
        resp = await client.post(
            f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
            params={"token": API_KEY, "timeout": timeout},
            json={
                "keyword": query,
                "maxItems": 10,
                "mode": mode,
            },
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            return []
        items = resp.json()
        if not isinstance(items, list):
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

    async with httpx.AsyncClient(timeout=35) as client:
        # Fetch sold + auctions in parallel with hard timeout
        sold_task = asyncio.create_task(_fetch_mode(client, query, "sold"))
        auction_task = asyncio.create_task(_fetch_mode(client, query, "weekly_auction"))
        buy_now_task = asyncio.create_task(_fetch_mode(client, query, "buy_now"))

        done, pending = await asyncio.wait(
            [sold_task, auction_task, buy_now_task],
            timeout=30,
            return_when=asyncio.ALL_COMPLETED,
        )

        for t in pending:
            t.cancel()

        if sold_task in done:
            results["sold"] = sold_task.result()
        if auction_task in done:
            results["auctions"] = auction_task.result()
        if buy_now_task in done:
            results["buy_now"] = buy_now_task.result()

    return {"error": None, **results}
