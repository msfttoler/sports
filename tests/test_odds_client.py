"""Tests for app.odds_client — The Odds API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import BookmakerOdds, Event, OddsOutcome
from app.odds_client import OddsClient


class TestOddsClientInit:
    """Tests for OddsClient constructor."""

    def test_init_sets_fields(self):
        with patch("app.odds_client.settings") as mock_settings:
            mock_settings.ODDS_API_BASE_URL = "https://example.com/v4"
            mock_settings.ODDS_API_KEY = "test-key"
            client = OddsClient()
            assert client.base_url == "https://example.com/v4"
            assert client.api_key == "test-key"


class TestParseEvents:
    """Tests for OddsClient._parse_events (static method)."""

    def test_parses_single_event(self, odds_api_response):
        events = OddsClient._parse_events(odds_api_response, "americanfootball_nfl")
        assert len(events) == 1
        ev = events[0]
        assert ev.id == "abc123"
        assert ev.home_team == "Chiefs"
        assert ev.away_team == "Bills"
        assert ev.sport_key == "americanfootball_nfl"

    def test_parses_bookmakers(self, odds_api_response):
        events = OddsClient._parse_events(odds_api_response, "nfl")
        ev = events[0]
        assert len(ev.bookmakers) == 1
        bm = ev.bookmakers[0]
        assert bm.bookmaker_key == "fanduel"
        assert bm.bookmaker_title == "FanDuel"
        assert bm.market == "h2h"

    def test_parses_outcomes(self, odds_api_response):
        events = OddsClient._parse_events(odds_api_response, "nfl")
        outcomes = events[0].bookmakers[0].outcomes
        assert len(outcomes) == 2
        names = {o.name for o in outcomes}
        assert "Chiefs" in names
        assert "Bills" in names

    def test_empty_data(self):
        events = OddsClient._parse_events([], "nfl")
        assert events == []

    def test_event_without_bookmakers(self):
        data = [
            {
                "id": "x1",
                "sport_key": "nfl",
                "sport_title": "NFL",
                "home_team": "H",
                "away_team": "A",
                "commence_time": "2026-01-01T00:00:00Z",
                "bookmakers": [],
            }
        ]
        events = OddsClient._parse_events(data, "nfl")
        assert len(events) == 1
        assert events[0].bookmakers == []

    def test_multiple_markets(self):
        data = [
            {
                "id": "m1",
                "sport_key": "nfl",
                "sport_title": "NFL",
                "home_team": "H",
                "away_team": "A",
                "commence_time": "2026-01-01T00:00:00Z",
                "bookmakers": [
                    {
                        "key": "fd",
                        "title": "FanDuel",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [{"name": "H", "price": -110}],
                            },
                            {
                                "key": "spreads",
                                "outcomes": [{"name": "H", "price": -110, "point": -3.5}],
                            },
                        ],
                    }
                ],
            }
        ]
        events = OddsClient._parse_events(data, "nfl")
        assert len(events[0].bookmakers) == 2
        markets = {bm.market for bm in events[0].bookmakers}
        assert "h2h" in markets
        assert "spreads" in markets

    def test_uses_fallback_sport_key(self):
        data = [
            {
                "id": "f1",
                "home_team": "H",
                "away_team": "A",
                "commence_time": "2026-01-01T00:00:00Z",
                "bookmakers": [],
            }
        ]
        events = OddsClient._parse_events(data, "fallback_key")
        assert events[0].sport_key == "fallback_key"
        assert events[0].sport_title == "fallback_key"


class TestPersistEvents:
    """Tests for OddsClient.persist_events."""

    @patch("app.odds_client.save_odds")
    def test_empty_events(self, mock_save):
        with patch("app.odds_client.settings"):
            client = OddsClient()
            client.persist_events([])
            mock_save.assert_called_once_with([])

    @patch("app.odds_client.save_odds")
    def test_flattens_events_to_rows(self, mock_save, sample_event):
        with patch("app.odds_client.settings"):
            client = OddsClient()
            client.persist_events([sample_event])
            mock_save.assert_called_once()
            rows = mock_save.call_args[0][0]
            assert len(rows) > 0
            row = rows[0]
            assert "sport_key" in row
            assert "event_id" in row
            assert "bookmaker" in row
            assert "outcome_name" in row
            assert "price" in row
            assert "fetched_at" in row

    @patch("app.odds_client.save_odds")
    def test_event_name_format(self, mock_save, sample_event):
        with patch("app.odds_client.settings"):
            client = OddsClient()
            client.persist_events([sample_event])
            rows = mock_save.call_args[0][0]
            assert rows[0]["event_name"] == "Team B @ Team A"


class TestGetOdds:
    """Tests for OddsClient.get_odds (async)."""

    @pytest.mark.asyncio
    async def test_calls_request_and_parses(self, odds_api_response):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"
            mock_s.REGIONS = "us"
            mock_s.MARKETS = "h2h"
            mock_s.ODDS_FORMAT = "american"

            client = OddsClient()
            client._request = AsyncMock(
                return_value=(odds_api_response, {"x-requests-used": "1", "x-requests-remaining": "499"})
            )

            with patch("app.odds_client.save_api_usage"):
                events, usage = await client.get_odds("nfl")

            assert len(events) == 1
            assert usage["remaining"] == "499"

    @pytest.mark.asyncio
    async def test_get_odds_saves_usage(self, odds_api_response):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"
            mock_s.REGIONS = "us"
            mock_s.MARKETS = "h2h"
            mock_s.ODDS_FORMAT = "american"

            client = OddsClient()
            client._request = AsyncMock(
                return_value=(odds_api_response, {"x-requests-used": "5", "x-requests-remaining": "495"})
            )

            with patch("app.odds_client.save_api_usage") as mock_save:
                await client.get_odds("nfl")
                mock_save.assert_called_once_with(5, 495)


class TestFetchAllSports:
    """Tests for OddsClient.fetch_all_sports (async)."""

    @pytest.mark.asyncio
    async def test_fetches_all_configured_sports(self):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"
            mock_s.SPORT_KEYS = {"NFL": "nfl", "NBA": "nba"}

            client = OddsClient()
            client.get_odds = AsyncMock(return_value=([], {}))

            events, usage = await client.fetch_all_sports()
            assert client.get_odds.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_sport_keys(self):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"

            client = OddsClient()
            client.get_odds = AsyncMock(return_value=([], {}))

            await client.fetch_all_sports(sport_keys=["nfl"])
            assert client.get_odds.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"
            mock_s.SPORT_KEYS = {"NFL": "nfl"}

            client = OddsClient()
            client.get_odds = AsyncMock(side_effect=Exception("network error"))

            events, usage = await client.fetch_all_sports()
            assert events == []


class TestGetSports:
    """Tests for OddsClient.get_sports (async)."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://api.example.com/v4"
            mock_s.ODDS_API_KEY = "key"

            client = OddsClient()
            client._request = AsyncMock(return_value=[{"key": "nfl", "title": "NFL"}])

            result = await client.get_sports()
            assert isinstance(result, list)
            assert result[0]["key"] == "nfl"
