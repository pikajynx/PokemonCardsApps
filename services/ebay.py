"""eBay sold listings via CompSniper API"""
import os
import httpx
from datetime import datetime, timezone

API_KEY = os.getenv("COMPSNIPER_API_KEY", "")
BASE_URL = "https://api.compsniper.com/v1"


def _parse_datetime(dt_str: str) -> datetime | None:
    """Parse various datetime formats from CompSniper/eBay."""
    if not dt_str:
        return None
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b-%d-%y %H:%M:%S %p",
    ]:
        try:
            return datetime.strptime(str(dt_str).strip(), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string like '3 days ago'."""
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "1 day ago"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks == 1:
        return "1 week ago"
    if days < 30:
        return f"{weeks} weeks ago"
    months = days // 30
    if months == 1:
        return "1 month ago"
    if months < 12:
        return f"{months} months ago"
    return f"{days // 365}y ago"


def _freshness_badge(dt: datetime) -> str:
    """Return freshness: green (<7d), yellow (7-30d), red (30+d)."""
    days = (datetime.now(timezone.utc) - dt).days
    if days < 7:
        return "green"
    elif days < 30:
        return "yellow"
    return "red"


async def get_ebay_sold(query: str, sold_after: str = "") -> dict:
    """Get recent eBay sold listings for a Pokémon card.
    
    Args:
        query: Search keyword
        sold_after: ISO date string (YYYY-MM-DD) to filter items sold after this date
    """
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
    
    # Add date range filter if provided
    if sold_after:
        params["soldAfter"] = sold_after

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/scrape",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            # Debug: try every possible key name
            listings = None
            for key in ["listings", "results", "items", "sold", "soldItems", "sold_items", "data", "rows"]:
                if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                    listings = data[key]
                    print(f"Found listings under key: {key}, count: {len(listings)}")
                    break
            
            if listings is None:
                # Fallback: print all keys and their types
                for k, v in data.items():
                    print(f"  key={k}, type={type(v).__name__}, len={len(v) if isinstance(v, list) else 'N/A'}")
                listings = []

            summary = data.get("summary", {})

            # Show all returned listings (CompSniper already returns recent ones)
            results = []
            for item in listings[:15]:
                price = item.get("soldPrice", item.get("price", ""))
                shipping = item.get("shippingPrice", "")
                total = item.get("totalPrice", "")
                
                # Extract all possible date fields
                ended_raw = item.get("endedAt", item.get("ended_at", item.get("soldDate", item.get("sold_date", ""))))
                listed_raw = item.get("listedDate", item.get("listed_date", item.get("startTime", item.get("start_time", ""))))
                
                # Parse dates
                ended_dt = _parse_datetime(ended_raw)
                listed_dt = _parse_datetime(listed_raw)
                
                # Calculate listing duration if both dates available
                listing_duration_days = None
                if ended_dt and listed_dt:
                    listing_duration_days = (ended_dt - listed_dt).days

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
                    # Full ISO datetime for structured data
                    "sold_date_iso": ended_dt.isoformat() if ended_dt else "",
                    "listed_date_iso": listed_dt.isoformat() if listed_dt else "",
                    # Human-readable formatted date
                    "sold_date_formatted": ended_dt.strftime("%b %d, %Y %I:%M %p") if ended_dt else "",
                    "listed_date_formatted": listed_dt.strftime("%b %d, %Y") if listed_dt else "",
                    # Relative time
                    "sold_relative": _relative_time(ended_dt) if ended_dt else "",
                    "listed_relative": _relative_time(listed_dt) if listed_dt else "",
                    # Freshness badge color
                    "freshness": _freshness_badge(ended_dt) if ended_dt else "",
                    # Listing duration
                    "listing_duration_days": listing_duration_days,
                    "listing_duration_text": f"{listing_duration_days}d" if listing_duration_days is not None else "",
                    # Keep raw for backward compat
                    "ended": ended_dt.strftime("%Y-%m-%d") if ended_dt else "",
                    "url": item.get("url", item.get("itemUrl", "")),
                    "image": item.get("image", item.get("imageUrl", "")),
                    "best_offer": item.get("bestOfferAccepted", item.get("best_offer_accepted", False)),
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
