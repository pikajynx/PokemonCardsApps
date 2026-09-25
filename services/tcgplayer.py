"""TCGPlayer price data via tcgapi.dev"""
import os
import httpx

API_KEY = os.getenv("TCGPLAYER_API_KEY", "")
BASE_URL = "https://api.tcgapi.dev/v1"


async def get_tcgplayer_prices(query: str) -> dict:
    """Search for a Pokémon card and return market price data."""
    if not API_KEY:
        return {"error": "TCGPlayer API key not configured", "results": []}

    headers = {"X-API-Key": API_KEY}
    params = {"q": query, "game": "pokemon", "limit": 5}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/search",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            cards = data.get("data", []) if isinstance(data, dict) else data

            for card in cards[:5]:
                results.append({
                    "name": card.get("name", "Unknown"),
                    "set": card.get("set_name", ""),
                    "number": card.get("number", ""),
                    "rarity": card.get("rarity", ""),
                    "image": card.get("image_url", ""),
                    "market_price": card.get("market_price", ""),
                    "low_price": card.get("low_price", ""),
                    "mid_price": card.get("median_price", ""),
                    "high_price": card.get("lowest_with_shipping", ""),
                })

            return {"error": None, "results": results}

        except httpx.HTTPStatusError as e:
            return {"error": f"TCGPlayer API error: {e.response.status_code}", "results": []}
        except Exception as e:
            return {"error": f"TCGPlayer: {str(e)}", "results": []}
