"""
Pokémon Card Price Checker — FastAPI app
Pulls prices from TCGPlayer, eBay (CompSniper), and Whatnot (Apify)
"""
import os
import asyncio
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.tcgplayer import get_tcgplayer_prices
from services.ebay import get_ebay_sold
from services.whatnot import get_whatnot_listings

app = FastAPI(title="Pokémon Card Price Checker")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query(default="", min_length=1)):
    query = q.strip()

    # Run all 3 API calls concurrently
    tcg_task = asyncio.create_task(get_tcgplayer_prices(query))
    ebay_task = asyncio.create_task(get_ebay_sold(query))
    whatnot_task = asyncio.create_task(get_whatnot_listings(query))

    tcg, ebay, whatnot = await asyncio.gather(
        tcg_task, ebay_task, whatnot_task, return_exceptions=True
    )

    # Handle exceptions gracefully
    if isinstance(tcg, Exception):
        tcg = {"error": str(tcg), "results": []}
    if isinstance(ebay, Exception):
        ebay = {"error": str(ebay), "results": []}
    if isinstance(whatnot, Exception):
        whatnot = {"error": str(whatnot), "results": []}

    return templates.TemplateResponse("results.html", {
        "request": request,
        "query": query,
        "tcg": tcg,
        "ebay": ebay,
        "whatnot": whatnot,
    })
