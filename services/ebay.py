"""eBay sold listings via CompSniper API"""
import os
import httpx

API_KEY = os.getenv("COMPSNIPER_API_KEY", "")
BASE_URL = "https://api.compsniper.com/v1"


async def get_ebay_sold(query: str) -> dict:
    """Get recent eBay sold listings for a Pokémon card."""
    if not API_KEY:
        return {"error": "CompSniper API key not configured", "results": []}

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {
        "keyword": f"pokemon {query}",
        "count": 30,
        "ebaySite": "ebay.com",
        "itemCondition": "any",
        "sold": "true",
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

            # Debug: log the response keys
            print(f"CompSniper response keys: {list(data.keys())}")
            print(f"CompSniper response (first 500 chars): {str(data)[:500]}")

            listings = data.get("listings", data.get("results", data.get("items", data.get("sold", []))))
            summary = data.get("summary", {})

            # Show all returned listings (CompSniper already returns recent ones)
            results = []
            for item in listings[:15]:
                price = item.get("soldPrice", item.get("price", ""))
                shipping = item.get("shippingPrice", "")
                total = item.get("totalPrice", "")
                ended = item.get("endedAt", item.get("ended_at", ""))

                if not total and price:
                    try:
                        p = float(str(price).replace(",", ""))
                        s = float(str(shipping).replace(",", "")) if shipping else 0
                        total = f"{p + s:.2f}"
                    except (ValueError, TypeError):
                        total = price

                results.append({
                    "title": item.get("title", ""),
                    "price": price,
                    "currency": item.get("soldCurrency", "USD"),
                    "shipping": shipping,
                    "total": total,
                    "condition": item.get("condition", ""),
                    "ended": ended[:10] if ended else "",
                    "url": item.get("url", item.get("itemUrl", "")),
                    "image": item.get("image", item.get("imageUrl", "")),
                })

            return {
                "error": None,
                "results": results,
                "summary": {
                    "median": summary.get("median", ""),
                    "average": summary.get("average", ""),
                    "count": summary.get("count", len(results)),
                    "p25": summary.get("p25", ""),
                    "p75": summary.get("p75", ""),
                },
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"eBay API error: {e.response.status_code}", "results": []}
        except Exception as e:
            return {"error": f"eBay: {str(e)}", "results": []}
