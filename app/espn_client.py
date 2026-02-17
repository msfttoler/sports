"""
ESPN Stats Client — fetches team records, scores, and schedules.

Uses the free ESPN API (no key required) to pull real sports data
for ML feature engineering.
"""

import logging
from datetime import UTC, datetime

import httpx

from app.models import TeamRecord

logger = logging.getLogger(__name__)

ESPN_SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports"
ESPN_V2_BASE = "https://site.api.espn.com/apis/v2/sports"

# Sport path mapping for ESPN API
ESPN_SPORTS = {
    "americanfootball_nfl": ("football", "nfl"),
    "basketball_nba": ("basketball", "nba"),
    "baseball_mlb": ("baseball", "mlb"),
    "icehockey_nhl": ("hockey", "nhl"),
    "americanfootball_ncaaf": ("football", "college-football"),
    "basketball_ncaab": ("basketball", "mens-college-basketball"),
    "soccer_epl": ("soccer", "eng.1"),
    "soccer_spain_la_liga": ("soccer", "esp.1"),
    "soccer_italy_serie_a": ("soccer", "ita.1"),
    "soccer_uefa_champs_league": ("soccer", "uefa.champions"),
}


class ESPNClient:
    """Fetch team stats and scores from ESPN's free API."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=20.0)

    async def close(self):
        await self._client.aclose()

    async def get_standings(self, sport_key: str) -> list[TeamRecord]:
        """Fetch current season standings for a sport."""
        if sport_key not in ESPN_SPORTS:
            logger.warning("Unknown sport key for ESPN: %s", sport_key)
            return []

        sport, league = ESPN_SPORTS[sport_key]
        url = f"{ESPN_V2_BASE}/{sport}/{league}/standings"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_standings(data, sport_key)
        except Exception as e:
            logger.error("Error fetching standings for %s: %s", sport_key, e)
            return []

    async def get_scoreboard(self, sport_key: str) -> list[dict]:
        """Fetch today's scoreboard (live + completed games)."""
        if sport_key not in ESPN_SPORTS:
            return []

        sport, league = ESPN_SPORTS[sport_key]
        url = f"{ESPN_SITE_BASE}/{sport}/{league}/scoreboard"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_scoreboard(data, sport_key)
        except Exception as e:
            logger.error("Error fetching scoreboard for %s: %s", sport_key, e)
            return []

    async def get_team_stats(self, sport_key: str) -> dict[str, TeamRecord]:
        """
        Get comprehensive team records for all teams in a league.
        Returns dict keyed by team display name.
        """
        records = await self.get_standings(sport_key)
        return {r.team: r for r in records}

    # ── Parsers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_standings(data: dict, sport_key: str) -> list[TeamRecord]:
        """Parse ESPN standings JSON into TeamRecord objects.

        The /apis/v2/ standings endpoint nests conferences under
        data['children'], each containing a 'standings' key with 'entries'.
        Stats come as a flat list with names like 'wins', 'losses',
        'avgPointsFor', 'avgPointsAgainst', 'differential', etc.
        """
        records: list[TeamRecord] = []

        # Collect entries from all conferences / groups
        all_entries: list[dict] = []
        for group in data.get("children", []):
            entries = group.get("standings", {}).get("entries", [])
            all_entries.extend(entries)

        # Fallback: flat standings at top level
        if not all_entries:
            all_entries = data.get("standings", {}).get("entries", [])

        for entry in all_entries:
            team_info = entry.get("team", {})
            team_name = team_info.get("displayName", "Unknown")
            stats_map: dict[str, str] = {}

            for stat in entry.get("stats", []):
                stats_map[stat.get("name", "")] = stat.get("displayValue", "0")

            try:
                wins = int(stats_map.get("wins", "0"))
                losses = int(stats_map.get("losses", "0"))
                ties = int(stats_map.get("ties", "0"))
                # ESPN v2 uses 'avgPointsFor' / 'avgPointsAgainst'
                # and sometimes 'pointsFor' / 'pointsAgainst'
                ppg = float(stats_map.get("avgPointsFor",
                            stats_map.get("pointsFor", "0")))
                opp_ppg = float(stats_map.get("avgPointsAgainst",
                                stats_map.get("pointsAgainst", "0")))
                # For total PF/PA, multiply avg by games if available
                total_games = wins + losses + ties
                pf = ppg * total_games if ppg < 200 else ppg   # heuristic: avg vs total
                pa = opp_ppg * total_games if opp_ppg < 200 else opp_ppg

                streak_str = stats_map.get("streak", "W0")
                streak_val = int(streak_str[1:]) if len(streak_str) > 1 else 0
                if streak_str.startswith("L"):
                    streak_val = -streak_val
            except (ValueError, IndexError):
                wins = losses = ties = 0
                pf = pa = 0.0
                streak_val = 0

            records.append(
                TeamRecord(
                    team=team_name,
                    wins=wins,
                    losses=losses,
                    ties=ties,
                    points_for=pf,
                    points_against=pa,
                    streak=streak_val,
                    sport_key=sport_key,
                )
            )

        logger.info("Parsed %d team records for %s", len(records), sport_key)
        return records

    @staticmethod
    def _parse_scoreboard(data: dict, sport_key: str) -> list[dict]:
        """Parse ESPN scoreboard into simplified game dicts."""
        games: list[dict] = []

        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            if len(competitors) < 2:
                continue

            home = away = None
            for c in competitors:
                info = {
                    "team": c.get("team", {}).get("displayName", ""),
                    "abbreviation": c.get("team", {}).get("abbreviation", ""),
                    "score": c.get("score", "0"),
                    "winner": c.get("winner", False),
                }
                if c.get("homeAway") == "home":
                    home = info
                else:
                    away = info

            if home and away:
                status = event.get("status", {}).get("type", {})
                games.append({
                    "event_id": event.get("id"),
                    "sport_key": sport_key,
                    "home_team": home["team"],
                    "away_team": away["team"],
                    "home_score": home["score"],
                    "away_score": away["score"],
                    "status": status.get("name", ""),
                    "completed": status.get("completed", False),
                    "commence_time": event.get("date", ""),
                })

        return games
