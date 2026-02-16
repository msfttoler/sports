"""
FastAPI application – Sports Arbitrage Finder.

Serves the web dashboard and API endpoints for odds and arbitrage data.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import (
    init_db,
    get_live_arbitrage,
    get_arbitrage_history,
    get_latest_odds,
    get_api_usage,
)
from app.scheduler import refresh_odds, start_scheduler, stop_scheduler, get_last_result

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    init_db()
    logger.info("Database initialized at %s", settings.DB_PATH)

    if settings.has_api_key:
        logger.info("API key found – running initial odds fetch…")
        await refresh_odds()
        start_scheduler()
    else:
        logger.warning(
            "No ODDS_API_KEY set. Add it to .env and restart. "
            "Dashboard will show demo mode."
        )

    yield

    # Shutdown
    stop_scheduler()


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sports Arbitrage Finder",
    description="Detect risk-free arbitrage opportunities across sportsbooks",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Dashboard ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    html_path = TEMPLATES_DIR / "dashboard.html"
    return HTMLResponse(content=html_path.read_text())


# ── API routes ────────────────────────────────────────────────────────

@app.get("/api/arbitrage")
async def api_arbitrage():
    """Return currently-live arbitrage opportunities."""
    arbs = get_live_arbitrage()
    # Parse legs JSON back to objects
    for a in arbs:
        if isinstance(a.get("legs"), str):
            a["legs"] = json.loads(a["legs"])
    return {"arbitrage": arbs, "count": len(arbs), "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/arbitrage/history")
async def api_arbitrage_history(limit: int = Query(50, ge=1, le=500)):
    """Return historical arbitrage opportunities."""
    arbs = get_arbitrage_history(limit)
    for a in arbs:
        if isinstance(a.get("legs"), str):
            a["legs"] = json.loads(a["legs"])
    return {"arbitrage": arbs, "count": len(arbs)}


@app.get("/api/odds")
async def api_odds(sport: str = Query(None)):
    """Return latest odds snapshot, optionally filtered by sport key."""
    sport_key = None
    if sport:
        sport_key = settings.SPORT_KEYS.get(sport.upper(), sport)
    rows = get_latest_odds(sport_key)
    return {"odds": rows, "count": len(rows)}


@app.post("/api/refresh")
async def api_refresh():
    """Manually trigger an odds refresh and arbitrage scan."""
    result = await refresh_odds()
    return result.model_dump()


@app.get("/api/status")
async def api_status():
    """Application status, config, and API usage."""
    usage = get_api_usage()
    last = get_last_result()
    return {
        "api_key_configured": settings.has_api_key,
        "refresh_interval_seconds": settings.REFRESH_INTERVAL,
        "sports_tracked": list(settings.SPORT_KEYS.keys()),
        "markets": settings.MARKETS,
        "regions": settings.REGIONS,
        "min_profit_pct": settings.MIN_PROFIT_PCT,
        "api_usage": usage,
        "last_refresh": last.model_dump() if last else None,
    }


@app.get("/api/sports")
async def api_sports():
    """Return the configured sports and their API keys."""
    return {"sports": settings.SPORT_KEYS}
