"""TCGPlayer price data via tcgapi.dev"""
import os
import httpx

API_KEY = os.getenv("TCGPLAYER_API_KEY", "")
BASE_URL = "https://api.tcgapi.dev/v1"


async def get_tcgplayer_prices(query: str) -> dict:
    """Search for a Pokémon card and return market price data."""
    if not API_KEY:
        return {"error": "TCGPlayer API key not configured", "results": []}

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"q": query, "game": "pokemon", "limit": 5}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            # Search for the card
            resp = await client.get(
                f"{BASE_URL}/cards/search",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            cards = data if isinstance(data, list) else data.get("data", data.get("results", []))

            for card in cards[:5]:
                name = card.get("name", "Unknown")
                set_name = card.get("set", {}).get("name", "") if isinstance(card.get("set"), dict) else str(card.get("set", ""))
                number = card.get("number", "")
                image = card.get("image", card.get("imageUrl", ""))

                # Get pricing
                prices = card.get("prices", card.get("tcgplayer", {}))
                if isinstance(prices, dict):
                    market = prices.get("market", prices.get("marketPrice", ""))
                    low = prices.get("low", prices.get("lowPrice", ""))
                    mid = prices.get("mid", prices.get("midPrice", ""))
                    high = prices.get("high", prices.get("highPrice", ""))
                else:
                    market = low = mid = high = ""

                results.append({
                    "name": name,
                    "set": set_name,
                    "number": number,
                    "image": image,
                    "market_price": market,
                    "low_price": low,
                    "mid_price": mid,
                    "high_price": high,
                })

            return {"error": None, "results": results}

        except httpx.HTTPStatusError as e:
            return {"error": f"TCGPlayer API error: {e.response.status_code}", "results": []}
        except Exception as e:
            return {"error": f"TCGPlayer: {str(e)}", "results": []}
