"""Whatnot listings via Apify Actor"""
import os
import httpx

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "crawloop~whatnot-listings-scraper"


async def get_whatnot_listings(query: str) -> dict:
    """Get current Whatnot listings for Pokemon cards."""
    if not API_KEY:
        return {"error": "Apify API key not configured", "results": []}

    async with httpx.AsyncClient(timeout=90) as client:
        try:
            resp = await client.post(
                f"https://api.apify.com/v2/actors/{ACTOR_ID}/run-sync-get-dataset-items",
                params={"token": API_KEY, "timeout": 60},
                json={
                    "searchKeywords": [f"pokemon {query}"],
                    "buyFormat": "buy_now",
                    "maxItems": 15,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            items = resp.json()

            if not isinstance(items, list):
                return {"error": "Unexpected Whatnot response", "results": []}

            results = []
            for item in items[:15]:
                results.append({
                    "title": item.get("title", ""),
                    "price": item.get("price", ""),
                    "currency": item.get("currency", "USD"),
                    "condition": item.get("condition", ""),
                    "seller": item.get("seller", item.get("sellerName", "")),
                    "rating": item.get("sellerRating", item.get("seller_rating", "")),
                    "live": item.get("live", False),
                    "url": item.get("url", item.get("itemUrl", "")),
                    "image": item.get("image", item.get("imageUrl", "")),
                    "buy_format": item.get("buyFormat", item.get("buy_format", "")),
                })

            return {"error": None, "results": results}

        except httpx.HTTPStatusError as e:
            return {"error": f"Whatnot API error: {e.response.status_code}", "results": []}
        except Exception as e:
            return {"error": f"Whatnot: {str(e)}", "results": []}
