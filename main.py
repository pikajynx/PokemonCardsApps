"""
Pokémon Card Price Checker — FastAPI app
Pulls prices from TCGPlayer, eBay (CompSniper), and Whatnot (Apify)
"""
import os
import asyncio
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.tcgplayer import get_tcgplayer_prices
from services.ebay import get_ebay_sold
from services.whatnot import get_whatnot_listings
from services.fanatics import get_fanatics_listings
from services.tiktok import get_tiktok_listings
from services.instagram import get_instagram_listings

app = FastAPI(title="Pokémon Card Price Checker")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = Query(default="", min_length=1),
    grade: str = Query(default=""),
):
    query = q.strip()
    grade = grade.strip()

    # Build graded search query
    ebay_query = f"{query} {grade}".strip() if grade else query
    whatnot_query = f"{query} {grade}".strip() if grade else query
    fanatics_query = f"{query} {grade}".strip() if grade else query
    social_query = f"{query} {grade}".strip() if grade else query

    # Run API calls concurrently
    tcg_task = asyncio.create_task(get_tcgplayer_prices(query))
    ebay_task = asyncio.create_task(get_ebay_sold(ebay_query))
    whatnot_task = asyncio.create_task(get_whatnot_listings(whatnot_query))
    fanatics_task = asyncio.create_task(get_fanatics_listings(fanatics_query))
    tiktok_task = asyncio.create_task(get_tiktok_listings(social_query))
    instagram_task = asyncio.create_task(get_instagram_listings(social_query))

    tcg, ebay, whatnot, fanatics, tiktok, instagram = await asyncio.gather(
        tcg_task, ebay_task, whatnot_task, fanatics_task, tiktok_task, instagram_task,
        return_exceptions=True
    )

    if isinstance(tcg, Exception):
        tcg = {"error": str(tcg), "results": []}
    if isinstance(ebay, Exception):
        ebay = {"error": str(ebay), "results": []}
    if isinstance(whatnot, Exception):
        whatnot = {"error": str(whatnot), "results": []}
    if isinstance(fanatics, Exception):
        fanatics = {"sold": [], "auctions": [], "buy_now": []}
    if isinstance(tiktok, Exception):
        tiktok = {"error": str(tiktok), "results": []}
    if isinstance(instagram, Exception):
        instagram = {"error": str(instagram), "results": []}

    return templates.TemplateResponse("results.html", {
        "request": request,
        "query": query,
        "grade": grade,
        "tcg": tcg,
        "ebay": ebay,
        "whatnot": whatnot,
        "fanatics": fanatics,
        "tiktok": tiktok,
        "instagram": instagram,
    })


@app.get("/debug/ebay")
async def debug_ebay(q: str = Query(default="pikachu")):
    """Debug endpoint to see raw CompSniper response."""
    import httpx
    API_KEY = os.getenv("COMPSNIPER_API_KEY", "")
    if not API_KEY:
        return JSONResponse({"error": "No API key set"})
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"keyword": f"pokemon {q}", "count": 5, "ebaySite": "ebay.com", "sold": "true"}
    
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://api.compsniper.com/v1/scrape", headers=headers, params=params)
        data = resp.json()
        
        result = {"status": resp.status_code, "keys": list(data.keys())}
        for k, v in data.items():
            if isinstance(v, list):
                result[f"{k}_count"] = len(v)
                if v and isinstance(v[0], dict):
                    result[f"{k}_fields"] = list(v[0].keys())
            elif isinstance(v, dict):
                result[f"{k}_keys"] = list(v.keys())
        
        return JSONResponse(result)
