"""
ESPN Injuries & Roster Client — fetches player injuries, statuses, and key stats.

Uses ESPN's free API to pull:
- Team injury reports (who's out, doubtful, questionable, probable)
- Key player stats (top scorers, leaders)
- Roster depth/impact analysis
"""

import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

ESPN_CORE = "https://site.api.espn.com/apis/site/v2/sports"

# Sport paths for ESPN
SPORT_PATHS = {
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


class InjuryReport:
    """Parsed injury data for a team."""

    def __init__(self, team: str):
        self.team = team
        self.out: list[dict] = []       # Definitely not playing
        self.doubtful: list[dict] = []  # Unlikely to play
        self.questionable: list[dict] = []  # Uncertain
        self.probable: list[dict] = []  # Likely to play
        self.day_to_day: list[dict] = []

    @property
    def total_out(self) -> int:
        return len(self.out) + len(self.doubtful)

    @property
    def total_questionable(self) -> int:
        return len(self.questionable) + len(self.day_to_day)

    @property
    def impact_score(self) -> float:
        """0-1 injury impact score. Higher = more players missing."""
        # Weight: out=1.0, doubtful=0.8, questionable=0.4, probable=0.1
        score = (
            len(self.out) * 1.0
            + len(self.doubtful) * 0.8
            + len(self.questionable) * 0.4
            + len(self.day_to_day) * 0.3
            + len(self.probable) * 0.1
        )
        # Normalize: 5+ injuries = max impact
        return min(score / 5.0, 1.0)

    def summary(self) -> str:
        parts = []
        if self.out:
            names = ", ".join(p["name"] for p in self.out[:3])
            parts.append(f"OUT: {names}" + (f" +{len(self.out)-3} more" if len(self.out) > 3 else ""))
        if self.doubtful:
            names = ", ".join(p["name"] for p in self.doubtful[:2])
            parts.append(f"DOUBTFUL: {names}")
        if self.questionable:
            parts.append(f"{len(self.questionable)} questionable")
        return "; ".join(parts) if parts else "No significant injuries"

    def to_dict(self) -> dict:
        return {
            "team": self.team,
            "out": self.out,
            "doubtful": self.doubtful,
            "questionable": self.questionable,
            "probable": self.probable,
            "day_to_day": self.day_to_day,
            "total_out": self.total_out,
            "total_questionable": self.total_questionable,
            "impact_score": round(self.impact_score, 3),
            "summary": self.summary(),
        }


class ESPNInjuryClient:
    """Fetch injury reports and player data from ESPN."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self._client.aclose()

    async def get_injuries(self, sport_key: str) -> dict[str, InjuryReport]:
        """
        Fetch injury reports for all teams in a sport.
        Returns dict keyed by team display name.
        """
        if sport_key not in SPORT_PATHS:
            return {}

        sport, league = SPORT_PATHS[sport_key]
        url = f"{ESPN_CORE}/{sport}/{league}/injuries"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_injuries(data)
        except Exception as e:
            logger.warning("Could not fetch injuries for %s: %s", sport_key, e)
            return {}

    async def get_team_roster_stats(
        self, sport_key: str, team_id: str
    ) -> list[dict]:
        """Fetch key player stats for a specific team."""
        if sport_key not in SPORT_PATHS:
            return []

        sport, league = SPORT_PATHS[sport_key]
        url = f"{ESPN_CORE}/{sport}/{league}/teams/{team_id}/roster"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_roster(data)
        except Exception as e:
            logger.debug("Could not fetch roster for team %s: %s", team_id, e)
            return []

    async def get_game_injuries(
        self, sport_key: str, home_team: str, away_team: str
    ) -> tuple[InjuryReport, InjuryReport]:
        """Get injury reports for both teams in a matchup."""
        all_injuries = await self.get_injuries(sport_key)

        home_report = all_injuries.get(home_team, InjuryReport(home_team))
        away_report = all_injuries.get(away_team, InjuryReport(away_team))

        # Fuzzy match if exact name didn't work
        if not home_report.out and not home_report.questionable:
            for name, report in all_injuries.items():
                if _fuzzy_match(home_team, name):
                    home_report = report
                    break

        if not away_report.out and not away_report.questionable:
            for name, report in all_injuries.items():
                if _fuzzy_match(away_team, name):
                    away_report = report
                    break

        return home_report, away_report

    # ── Parsers ───────────────────────────────────────────────────

    @staticmethod
    def _parse_injuries(data: dict) -> dict[str, InjuryReport]:
        """Parse ESPN injuries response."""
        reports: dict[str, InjuryReport] = {}

        for team_entry in data.get("injuries", []):
            team_info = team_entry.get("team", {})
            team_name = team_info.get("displayName", "Unknown")
            report = InjuryReport(team_name)

            for item in team_entry.get("injuries", []):
                player = {
                    "name": item.get("athlete", {}).get("displayName", "Unknown"),
                    "position": item.get("athlete", {}).get("position", {}).get("abbreviation", ""),
                    "status": item.get("status", ""),
                    "injury": item.get("details", {}).get("type", ""),
                    "detail": item.get("details", {}).get("detail", ""),
                }

                status = player["status"].lower()
                if status in ("out", "injured reserve", "ir", "suspension"):
                    report.out.append(player)
                elif status == "doubtful":
                    report.doubtful.append(player)
                elif status == "questionable":
                    report.questionable.append(player)
                elif status in ("probable", "available"):
                    report.probable.append(player)
                elif status in ("day-to-day", "day to day"):
                    report.day_to_day.append(player)
                else:
                    report.questionable.append(player)

            reports[team_name] = report

        logger.info("Parsed injury reports for %d teams", len(reports))
        return reports

    @staticmethod
    def _parse_roster(data: dict) -> list[dict]:
        """Parse ESPN roster response into player stat dicts."""
        players = []
        for group in data.get("athletes", []):
            for athlete in group.get("items", []):
                players.append({
                    "name": athlete.get("displayName", ""),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "jersey": athlete.get("jersey", ""),
                    "age": athlete.get("age"),
                    "experience": athlete.get("experience", {}).get("years", 0),
                })
        return players


def _fuzzy_match(a: str, b: str) -> bool:
    """Check if two team names match fuzzily."""
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    if a_lower == b_lower:
        return True
    if a_lower in b_lower or b_lower in a_lower:
        return True
    # Last word match (e.g. "Pistons" in "Detroit Pistons")
    a_last = a_lower.split()[-1] if a_lower else ""
    b_last = b_lower.split()[-1] if b_lower else ""
    if a_last and len(a_last) > 3 and (a_last in b_lower or b_last in a_lower):
        return True
    return False
