"""
FastAPI application – Sports Arbitrage Finder.

Serves the web dashboard and API endpoints for odds and arbitrage data.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.models import Event
from app.database import (
    init_db,
    get_live_arbitrage,
    get_arbitrage_history,
    get_latest_odds,
    get_api_usage,
    add_bet,
    settle_bet,
    get_all_bets,
    get_bet_summary,
)
from app.scheduler import refresh_odds, start_scheduler, stop_scheduler, get_last_result
from app.espn_client import ESPNClient
from app.injuries import ESPNInjuryClient
from app.predictor import predict_events, predict_game, build_features, add_injury_features
from app.value_bets import find_value_bets

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


# ── Prediction routes ─────────────────────────────────────────────────

@app.get("/api/predictions")
async def api_predictions(sport: str = Query("NFL")):
    """
    AI-powered game predictions with confidence scores.

    Fetches live odds + ESPN stats, runs the prediction engine,
    and cross-references with book odds for value bets.
    """
    sport_key = settings.SPORT_KEYS.get(sport.upper(), sport)

    # Fetch team stats from ESPN
    espn = ESPNClient()
    try:
        team_stats = await espn.get_team_stats(sport_key)
    finally:
        await espn.close()

    # Get current events with odds (from last refresh)
    from app.odds_client import OddsClient
    events = []
    odds_error = ""
    if settings.has_api_key:
        client = OddsClient()
        try:
            # Fetch both moneyline and spreads for spread coverage analysis
            events, _ = await client.get_odds(sport_key, markets="h2h,spreads")
        except Exception as e:
            odds_error = str(e)
            logger.error("Error fetching odds for predictions: %s", e)
        finally:
            await client.close()

    # Fallback: if no odds events, create matchups from ESPN scoreboard
    if not events and team_stats:
        espn2 = ESPNClient()
        try:
            scoreboard = await espn2.get_scoreboard(sport_key)
            for g in scoreboard:
                if not g.get("completed"):
                    events.append(Event(
                        id=g.get("event_id", ""),
                        sport_key=sport_key,
                        sport_title=sport.upper(),
                        home_team=g["home_team"],
                        away_team=g["away_team"],
                        commence_time=g.get("commence_time", ""),
                    ))
            if not events:
                # No live games either — create demo matchups from standings
                sorted_teams = sorted(team_stats.values(), key=lambda r: r.win_pct, reverse=True)
                for i in range(0, min(len(sorted_teams) - 1, 14), 2):
                    events.append(Event(
                        id=f"demo_{i}",
                        sport_key=sport_key,
                        sport_title=sport.upper(),
                        home_team=sorted_teams[i].team,
                        away_team=sorted_teams[i + 1].team,
                        commence_time="",
                    ))
        except Exception as e:
            logger.error("Error fetching ESPN scoreboard: %s", e)
        finally:
            await espn2.close()

    # Fetch injury reports from ESPN
    injury_client = ESPNInjuryClient()
    injury_data: dict = {}
    try:
        injury_reports = await injury_client.get_injuries(sport_key)
        injury_data = {name: r.to_dict() for name, r in injury_reports.items()}
    except Exception as e:
        logger.warning("Could not fetch injuries: %s", e)
    finally:
        await injury_client.close()

    # Run predictions (injuries included in feature engineering)
    predictions = predict_events(events, team_stats, injury_reports=injury_reports if injury_data else None)

    # Find value bets
    value_bets = find_value_bets(predictions, events)

    return {
        "predictions": [p.model_dump() for p in predictions],
        "value_bets": [v.model_dump() for v in value_bets],
        "prediction_count": len(predictions),
        "value_bet_count": len(value_bets),
        "teams_with_stats": len(team_stats),
        "injuries_loaded": len(injury_data),
        "sport": sport.upper(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/standings")
async def api_standings(sport: str = Query("NFL")):
    """Get current team standings from ESPN."""
    sport_key = settings.SPORT_KEYS.get(sport.upper(), sport)
    espn = ESPNClient()
    try:
        records = await espn.get_team_stats(sport_key)
    finally:
        await espn.close()

    # Sort by win percentage
    sorted_teams = sorted(records.values(), key=lambda r: r.win_pct, reverse=True)

    return {
        "standings": [
            {
                "team": r.team,
                "record": f"{r.wins}-{r.losses}" + (f"-{r.ties}" if r.ties else ""),
                "win_pct": round(r.win_pct, 3),
                "ppg": round(r.ppg, 1),
                "opp_ppg": round(r.opp_ppg, 1),
                "point_diff": round(r.point_diff, 1),
                "streak": r.streak,
            }
            for r in sorted_teams
        ],
        "count": len(sorted_teams),
        "sport": sport.upper(),
    }


@app.get("/api/injuries")
async def api_injuries(sport: str = Query("NBA")):
    """Get current injury reports from ESPN."""
    sport_key = settings.SPORT_KEYS.get(sport.upper(), sport)
    client = ESPNInjuryClient()
    try:
        reports = await client.get_injuries(sport_key)
    finally:
        await client.close()

    return {
        "injuries": {name: r.to_dict() for name, r in reports.items()},
        "teams_with_injuries": sum(1 for r in reports.values() if r.total_out > 0),
        "sport": sport.upper(),
    }


# ── Bet Tracker routes ────────────────────────────────────────────────

@app.post("/api/bets")
async def api_add_bet(request: Request):
    """Add a new bet to the tracker."""
    body = await request.json()
    required = ["sport", "event_name", "bet_type", "pick", "odds", "stake"]
    for field in required:
        if field not in body:
            return {"error": f"Missing required field: {field}"}, 400

    odds_val = int(body["odds"])
    stake_val = float(body["stake"])

    # Calculate potential win from American odds + stake
    if odds_val > 0:
        potential_win = stake_val * (odds_val / 100.0)
    else:
        potential_win = stake_val * (100.0 / abs(odds_val))

    bet_data = {
        "sport": body["sport"],
        "event_name": body["event_name"],
        "home_team": body.get("home_team", ""),
        "away_team": body.get("away_team", ""),
        "bet_type": body.get("bet_type", "moneyline"),
        "pick": body["pick"],
        "spread_line": body.get("spread_line"),
        "total_line": body.get("total_line"),
        "odds": odds_val,
        "stake": stake_val,
        "potential_win": round(potential_win, 2),
        "our_confidence": body.get("confidence"),
        "notes": body.get("notes", ""),
    }

    bet_id = add_bet(bet_data)
    return {"id": bet_id, "potential_win": round(potential_win, 2), "status": "pending"}


@app.post("/api/bets/{bet_id}/settle")
async def api_settle_bet(bet_id: int, request: Request):
    """Settle a bet as win, loss, or push."""
    body = await request.json()
    result = body.get("result", "").lower()
    if result not in ("win", "loss", "push"):
        return {"error": "result must be 'win', 'loss', or 'push'"}

    bet = settle_bet(bet_id, result)
    if not bet:
        return {"error": "Bet not found"}
    return bet


@app.get("/api/bets")
async def api_get_bets(limit: int = Query(200, ge=1, le=1000)):
    """Get all tracked bets."""
    bets = get_all_bets(limit)
    summary = get_bet_summary()
    return {"bets": bets, "summary": summary}


@app.post("/api/bets/auto-settle")
async def api_auto_settle():
    """Check ESPN scores and auto-settle any matching pending bets."""
    from app.auto_settle import auto_settle_bets
    result = await auto_settle_bets()
    return result
