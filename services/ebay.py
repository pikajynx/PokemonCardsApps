"""eBay sold listings via CompSniper API"""
import os
import httpx
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("COMPSNIPER_API_KEY", "")
BASE_URL = "https://api.compsniper.com/v1"


async def get_ebay_sold(query: str) -> dict:
    """Get recent eBay sold listings for a Pokémon card."""
    if not API_KEY:
        return {"error": "CompSniper API key not configured", "results": []}

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {
        "keyword": f"pokemon {query}",
        "count": 20,
        "ebaySite": "ebay.com",
        "itemCondition": "any",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/scrape",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            listings = data.get("listings", data.get("results", []))
            summary = data.get("summary", {})

            # Filter to last 3 days
            three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
            recent = []
            for item in listings:
                ended = item.get("endedAt", item.get("ended_at", ""))
                if ended:
                    try:
                        ended_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
                        if ended_dt < three_days_ago:
                            continue
                    except (ValueError, TypeError):
                        pass

                recent.append({
                    "title": item.get("title", ""),
                    "price": item.get("soldPrice", item.get("price", "")),
                    "currency": item.get("soldCurrency", "USD"),
                    "shipping": item.get("shippingPrice", ""),
                    "total": item.get("totalPrice", ""),
                    "condition": item.get("condition", ""),
                    "ended": ended,
                    "url": item.get("url", item.get("itemUrl", "")),
                    "image": item.get("image", item.get("imageUrl", "")),
                })

            return {
                "error": None,
                "results": recent[:15],
                "summary": {
                    "median": summary.get("median", ""),
                    "average": summary.get("average", ""),
                    "count": summary.get("count", len(recent)),
                    "p25": summary.get("p25", ""),
                    "p75": summary.get("p75", ""),
                },
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"eBay API error: {e.response.status_code}", "results": []}
        except Exception as e:
            return {"error": f"eBay: {str(e)}", "results": []}
