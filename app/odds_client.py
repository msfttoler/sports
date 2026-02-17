"""
Client for The Odds API (https://the-odds-api.com).
Fetches live odds from multiple sportsbooks for arbitrage analysis.
"""

import logging
from datetime import UTC, datetime

import httpx

from app.config import settings
from app.models import Event, BookmakerOdds, OddsOutcome
from app.database import save_odds, save_api_usage

logger = logging.getLogger(__name__)


class OddsClient:
    """HTTP client for The Odds API."""

    def __init__(self):
        self.base_url = settings.ODDS_API_BASE_URL
        self.api_key = settings.ODDS_API_KEY
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_sports(self) -> list[dict]:
        """List all available sports on The Odds API."""
        resp = await self._request("GET", "/sports", params={"apiKey": self.api_key})
        return resp

    async def get_odds(
        self,
        sport_key: str,
        regions: str | None = None,
        markets: str | None = None,
        odds_format: str | None = None,
    ) -> tuple[list[Event], dict]:
        """
        Fetch current odds for a sport.

        Returns:
            (list[Event], response_headers_dict)
        """
        params = {
            "apiKey": self.api_key,
            "regions": regions or settings.REGIONS,
            "markets": markets or settings.MARKETS,
            "oddsFormat": odds_format or settings.ODDS_FORMAT,
        }
        data, headers = await self._request(
            "GET", f"/sports/{sport_key}/odds", params=params, return_headers=True
        )

        # Track API usage from response headers
        usage = {
            "used": headers.get("x-requests-used"),
            "remaining": headers.get("x-requests-remaining"),
        }
        if usage["remaining"] is not None:
            try:
                save_api_usage(int(usage["used"]), int(usage["remaining"]))
            except Exception:
                pass

        events = self._parse_events(data, sport_key)
        return events, usage

    async def fetch_all_sports(
        self,
        sport_keys: list[str] | None = None,
    ) -> tuple[list[Event], dict]:
        """
        Fetch odds for multiple sports.  Returns combined events list
        and the latest usage dict.
        """
        keys = sport_keys or list(settings.SPORT_KEYS.values())
        all_events: list[Event] = []
        latest_usage: dict = {}

        for key in keys:
            try:
                events, usage = await self.get_odds(key)
                all_events.extend(events)
                latest_usage = usage
                logger.info("Fetched %d events for %s", len(events), key)
            except Exception as e:
                logger.error("Error fetching odds for %s: %s", key, e)

        return all_events, latest_usage

    # ------------------------------------------------------------------
    # Persistence helper – flatten events into DB rows
    # ------------------------------------------------------------------

    def persist_events(self, events: list[Event]):
        """Flatten events into rows and save to SQLite."""
        now = datetime.now(UTC).isoformat()
        rows: list[dict] = []

        for ev in events:
            for bm in ev.bookmakers:
                for outcome in bm.outcomes:
                    rows.append(
                        {
                            "sport_key": ev.sport_key,
                            "event_id": ev.id,
                            "event_name": f"{ev.away_team} @ {ev.home_team}",
                            "home_team": ev.home_team,
                            "away_team": ev.away_team,
                            "commence_time": ev.commence_time,
                            "bookmaker": bm.bookmaker_title,
                            "market": bm.market,
                            "outcome_name": outcome.name,
                            "price": outcome.price,
                            "point": outcome.point,
                            "fetched_at": now,
                        }
                    )

        save_odds(rows)
        logger.info("Persisted %d odds rows", len(rows))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, params: dict | None = None, *, return_headers: bool = False):
        url = f"{self.base_url}{path}"
        resp = await self._client.request(method, url, params=params)
        resp.raise_for_status()
        if return_headers:
            return resp.json(), dict(resp.headers)
        return resp.json()

    @staticmethod
    def _parse_events(data: list[dict], sport_key: str) -> list[Event]:
        events: list[Event] = []
        for item in data:
            bookmakers: list[BookmakerOdds] = []
            for bm in item.get("bookmakers", []):
                for market in bm.get("markets", []):
                    outcomes = [
                        OddsOutcome(
                            name=o["name"],
                            price=o["price"],
                            point=o.get("point"),
                        )
                        for o in market.get("outcomes", [])
                    ]
                    bookmakers.append(
                        BookmakerOdds(
                            bookmaker_key=bm["key"],
                            bookmaker_title=bm["title"],
                            market=market["key"],
                            outcomes=outcomes,
                            last_update=bm.get("last_update"),
                        )
                    )

            events.append(
                Event(
                    id=item["id"],
                    sport_key=item.get("sport_key", sport_key),
                    sport_title=item.get("sport_title", sport_key),
                    home_team=item["home_team"],
                    away_team=item["away_team"],
                    commence_time=item["commence_time"],
                    bookmakers=bookmakers,
                )
            )
        return events
