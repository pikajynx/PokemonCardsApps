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
async def search(
    request: Request,
    q: str = Query(default="", min_length=1),
    grade: str = Query(default=""),
):
    query = q.strip()
    grade = grade.strip()

    # Build graded search query for eBay and Whatnot
    ebay_query = f"{query} {grade}".strip() if grade else query
    whatnot_query = f"{query} {grade}".strip() if grade else query

    # Run all 3 API calls concurrently
    tcg_task = asyncio.create_task(get_tcgplayer_prices(query))
    ebay_task = asyncio.create_task(get_ebay_sold(ebay_query))
    whatnot_task = asyncio.create_task(get_whatnot_listings(whatnot_query))

    tcg, ebay, whatnot = await asyncio.gather(
        tcg_task, ebay_task, whatnot_task, return_exceptions=True
    )

    if isinstance(tcg, Exception):
        tcg = {"error": str(tcg), "results": []}
    if isinstance(ebay, Exception):
        ebay = {"error": str(ebay), "results": []}
    if isinstance(whatnot, Exception):
        whatnot = {"error": str(whatnot), "results": []}

    return templates.TemplateResponse("results.html", {
        "request": request,
        "query": query,
        "grade": grade,
        "tcg": tcg,
        "ebay": ebay,
        "whatnot": whatnot,
    })
