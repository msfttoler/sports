"""
Auto-settle service — checks ESPN scores and settles pending bets.

Runs periodically (or on-demand) to:
1. Get all pending bets
2. For each sport with pending bets, fetch the ESPN scoreboard
3. Match completed games to pending bets by team names
4. Settle bets based on final scores
"""

import logging

from app.config import settings
from app.database import get_pending_bets, auto_settle_with_score
from app.espn_client import ESPNClient

logger = logging.getLogger(__name__)

# Map sport display names → Odds API sport keys → ESPN paths
SPORT_LABEL_TO_KEY: dict[str, str] = {
    v: k for k, v in {
        "americanfootball_nfl": "NFL",
        "basketball_nba": "NBA",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
        "americanfootball_ncaaf": "NCAAF",
        "basketball_ncaab": "NCAAM",
        "soccer_epl": "EPL",
        "soccer_spain_la_liga": "LA LIGA",
        "soccer_italy_serie_a": "SERIE A",
        "soccer_uefa_champs_league": "UCL",
    }.items()
}

# Reverse: label → sport_key
LABEL_TO_SPORT_KEY: dict[str, str] = {
    v: k for k, v in SPORT_LABEL_TO_KEY.items()
}


async def auto_settle_bets() -> dict:
    """
    Check ESPN scores and auto-settle any matching pending bets.

    Returns a summary of what was settled.
    """
    pending = get_pending_bets()
    if not pending:
        return {"settled": 0, "pending": 0, "message": "No pending bets"}

    # Group pending bets by sport label
    sports_needed: set[str] = set()
    for bet in pending:
        sports_needed.add(bet["sport"].upper())

    # Fetch scoreboards for each sport
    espn = ESPNClient()
    completed_games: list[dict] = []
    try:
        for sport_label in sports_needed:
            sport_key = LABEL_TO_SPORT_KEY.get(sport_label)
            if not sport_key:
                # Try direct lookup in settings
                sport_key = settings.SPORT_KEYS.get(sport_label)
            if not sport_key:
                continue

            games = await espn.get_scoreboard(sport_key)
            for g in games:
                if g.get("completed"):
                    completed_games.append(g)

        logger.info(
            "Auto-settle: %d pending bets, %d completed games found",
            len(pending), len(completed_games),
        )
    finally:
        await espn.close()

    if not completed_games:
        return {
            "settled": 0,
            "pending": len(pending),
            "message": "No completed games found on today's scoreboard",
        }

    # Try to match each pending bet to a completed game
    settled_count = 0
    results: list[dict] = []

    for bet in pending:
        match = _find_matching_game(bet, completed_games)
        if not match:
            continue

        try:
            home_score = int(match["home_score"])
            away_score = int(match["away_score"])
        except (ValueError, TypeError):
            continue

        settled = auto_settle_with_score(bet["id"], home_score, away_score)
        if settled and settled["result"] != "pending":
            settled_count += 1
            results.append({
                "bet_id": bet["id"],
                "event": bet["event_name"],
                "pick": bet["pick"],
                "score": f"{match['home_team']} {home_score} - {match['away_team']} {away_score}",
                "result": settled["result"],
                "pnl": settled["actual_pnl"],
            })
            logger.info(
                "Auto-settled bet #%d: %s → %s (score: %d-%d, P&L: %+.2f)",
                bet["id"],
                bet["pick"],
                settled["result"],
                home_score,
                away_score,
                settled["actual_pnl"],
            )

    return {
        "settled": settled_count,
        "pending": len(pending) - settled_count,
        "results": results,
        "games_checked": len(completed_games),
    }


def _find_matching_game(bet: dict, games: list[dict]) -> dict | None:
    """
    Find a completed game that matches a pending bet.

    Matches by checking if both team names from the bet appear in the game.
    """
    bet_event = bet.get("event_name", "").lower()
    bet_home = (bet.get("home_team") or "").lower()
    bet_away = (bet.get("away_team") or "").lower()
    bet_pick = bet.get("pick", "").lower()

    for game in games:
        game_home = game.get("home_team", "").lower()
        game_away = game.get("away_team", "").lower()

        # Strategy 1: match home_team + away_team fields directly
        if bet_home and bet_away:
            if (_fuzzy_team(bet_home, game_home) and _fuzzy_team(bet_away, game_away)):
                return game
            if (_fuzzy_team(bet_home, game_away) and _fuzzy_team(bet_away, game_home)):
                return game

        # Strategy 2: match from event_name (e.g. "Team A vs Team B")
        if game_home and game_away:
            if _fuzzy_team(game_home, bet_event) and _fuzzy_team(game_away, bet_event):
                return game

        # Strategy 3: match from pick + event_name
        if _fuzzy_team(game_home, bet_pick) or _fuzzy_team(game_away, bet_pick):
            if _fuzzy_team(game_home, bet_event) or _fuzzy_team(game_away, bet_event):
                return game

    return None


def _fuzzy_team(team: str, text: str) -> bool:
    """Check if a team name (or its last word) appears in text."""
    if not team or not text:
        return False
    team = team.lower().strip()
    text = text.lower().strip()
    if team in text:
        return True
    # Try last word (e.g. "Pistons" from "Detroit Pistons")
    last_word = team.split()[-1] if team else ""
    if last_word and len(last_word) > 3 and last_word in text:
        return True
    return False
