"""Whatnot listings via Apify Actor"""
import os
import httpx

API_KEY = os.getenv("APIFY_API_KEY", "")
ACTOR_ID = "crawloop/whatnot-listings-scraper"


async def get_whatnot_listings(query: str) -> dict:
    """Get current Whatnot listings for Pokémon cards."""
    if not API_KEY:
        return {"error": "Apify API key not configured", "results": []}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            # Start the Actor run
            run_resp = await client.post(
                f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
                params={"token": API_KEY},
                json={
                    "searchKeywords": f"pokemon {query}",
                    "buyFormat": "buy_now",
                    "maxItems": 15,
                },
            )
            run_resp.raise_for_status()
            run_data = run_resp.json()
            run_id = run_data.get("data", {}).get("id")

            if not run_id:
                return {"error": "Failed to start Whatnot scraper", "results": []}

            # Poll for completion (max 45 seconds)
            import asyncio
            for _ in range(15):
                await asyncio.sleep(3)
                status_resp = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": API_KEY},
                )
                status_data = status_resp.json()
                status = status_data.get("data", {}).get("status")
                if status == "SUCCEEDED":
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    return {"error": f"Whatnot scraper {status}", "results": []}

            # Get the results
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                return {"error": "No Whatnot results found", "results": []}

            items_resp = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                params={"token": API_KEY, "format": "json"},
            )
            items_resp.raise_for_status()
            items = items_resp.json()

            results = []
            for item in items[:15]:
                results.append({
                    "title": item.get("title", ""),
                    "price": item.get("price", ""),
                    "currency": item.get("currency", "USD"),
                    "condition": item.get("condition", ""),
                    "seller": item.get("seller", ""),
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
