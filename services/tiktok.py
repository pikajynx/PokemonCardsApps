"""TikTok hashtag search via Apify"""
import os
import httpx
import asyncio

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "clockworks~tiktok-scraper"


async def get_tiktok_listings(query: str) -> dict:
    """Search TikTok for card sales posts."""
    results = []
    if not API_KEY:
        return {"error": None, "results": results}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 25},
                json={
                    "searchQueries": [f"pokemon {query} for sale"],
                    "maxResults": 10,
                    "shouldDownloadVideos": False,
                    "shouldDownloadCovers": False,
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {"error": None, "results": results}

            items = resp.json()
            if not isinstance(items, list):
                return {"error": None, "results": results}

            for item in items[:10]:
                desc = item.get("text", item.get("description", ""))
                # Try to extract price from description
                price = _extract_price(desc)
                if price:
                    results.append({
                        "title": desc[:100],
                        "price": price,
                        "author": item.get("authorMeta", {}).get("name", item.get("author", "")),
                        "likes": item.get("diggCount", item.get("likes", "")),
                        "url": item.get("webVideoUrl", item.get("url", "")),
                    })
    except Exception:
        return {"error": None, "results": results}

    return {"error": None, "results": results}


def _extract_price(text: str) -> str:
    """Try to find a price in text."""
    import re
    if not text:
        return ""
    # Look for $XX.XX or $XX patterns
    matches = re.findall(r'\$[\d,]+\.?\d*', text)
    return matches[0] if matches else ""