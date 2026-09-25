"""Instagram hashtag search via Apify"""
import os
import httpx
import re

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "apify~instagram-scraper"


async def get_instagram_listings(query: str) -> dict:
    """Search Instagram for card sales posts."""
    results = []
    if not API_KEY:
        return {"error": None, "results": results}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 25},
                json={
                    "search": f"pokemon {query} for sale",
                    "searchType": "hashtag",
                    "searchLimit": 10,
                    "resultsType": "posts",
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {"error": None, "results": results}

            items = resp.json()
            if not isinstance(items, list):
                return {"error": None, "results": results}

            for item in items[:10]:
                caption = item.get("caption", item.get("text", ""))
                price = _extract_price(caption)
                if price:
                    results.append({
                        "title": caption[:100],
                        "price": price,
                        "author": item.get("ownerUsername", item.get("author", "")),
                        "likes": item.get("likesCount", item.get("likes", "")),
                        "url": item.get("url", ""),
                    })
    except Exception:
        return {"error": None, "results": results}

    return {"error": None, "results": results}


def _extract_price(text: str) -> str:
    if not text:
        return ""
    matches = re.findall(r'\$[\d,]+\.?\d*', text)
    return matches[0] if matches else ""