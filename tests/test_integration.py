"""
Integration tests for async infrastructure paths.

Covers the scheduler loop, lifespan hooks, and httpx request/close paths
that unit tests can't easily reach.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.models import RefreshResult
import app.scheduler as scheduler_module


# ═══════════════════════════════════════════════════════════════════════
# OddsClient — _request and close
# ═══════════════════════════════════════════════════════════════════════

class TestOddsClientRequest:
    """Integration tests for OddsClient._request and close."""

    @pytest.mark.asyncio
    async def test_request_json_response(self):
        """_request returns parsed JSON from a real httpx round-trip."""
        from app.odds_client import OddsClient

        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"sports": ["nfl"]})
        )
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://mock.api"
            mock_s.ODDS_API_KEY = "key"
            client = OddsClient()
            client._client = httpx.AsyncClient(transport=transport)

            result = await client._request("GET", "/sports", params={"apiKey": "key"})
            assert result == {"sports": ["nfl"]}
            await client.close()

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """_request returns (json, headers) when return_headers=True."""
        from app.odds_client import OddsClient

        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json=[{"id": "e1"}],
                headers={"x-requests-used": "3", "x-requests-remaining": "497"},
            )
        )
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://mock.api"
            mock_s.ODDS_API_KEY = "key"
            client = OddsClient()
            client._client = httpx.AsyncClient(transport=transport)

            data, headers = await client._request(
                "GET", "/sports/nfl/odds", params={"apiKey": "key"}, return_headers=True
            )
            assert isinstance(data, list)
            assert headers["x-requests-used"] == "3"
            await client.close()

    @pytest.mark.asyncio
    async def test_request_raises_on_http_error(self):
        """_request raises httpx.HTTPStatusError on 4xx/5xx."""
        from app.odds_client import OddsClient

        transport = httpx.MockTransport(
            lambda req: httpx.Response(401, json={"error": "unauthorized"})
        )
        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://mock.api"
            mock_s.ODDS_API_KEY = "bad"
            client = OddsClient()
            client._client = httpx.AsyncClient(transport=transport)

            with pytest.raises(httpx.HTTPStatusError):
                await client._request("GET", "/sports")
            await client.close()

    @pytest.mark.asyncio
    async def test_close_can_be_called_safely(self):
        """close() doesn't raise even when called multiple times."""
        from app.odds_client import OddsClient

        with patch("app.odds_client.settings") as mock_s:
            mock_s.ODDS_API_BASE_URL = "https://mock.api"
            mock_s.ODDS_API_KEY = "key"
            client = OddsClient()
            await client.close()
            # Second close should not raise — httpx handles this

    @pytest.mark.asyncio
    async def test_get_odds_full_roundtrip(self):
        """get_odds performs a full round-trip with mock transport."""
        from app.odds_client import OddsClient

        api_response = [
            {
                "id": "evt1",
                "sport_key": "americanfootball_nfl",
                "sport_title": "NFL",
                "home_team": "Chiefs",
                "away_team": "Bills",
                "commence_time": "2026-02-16T18:00:00Z",
                "bookmakers": [
                    {
                        "key": "fanduel",
                        "title": "FanDuel",
                        "last_update": "2026-02-16T12:00:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Chiefs", "price": -150},
                                    {"name": "Bills", "price": 130},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json=api_response,
                headers={"x-requests-used": "1", "x-requests-remaining": "499"},
            )
        )
        with (
            patch("app.odds_client.settings") as mock_s,
            patch("app.odds_client.save_api_usage") as mock_save_usage,
            patch("app.odds_client.save_odds"),
        ):
            mock_s.ODDS_API_BASE_URL = "https://mock.api"
            mock_s.ODDS_API_KEY = "key"
            mock_s.REGIONS = "us"
            mock_s.MARKETS = "h2h"
            mock_s.ODDS_FORMAT = "american"

            client = OddsClient()
            client._client = httpx.AsyncClient(transport=transport)

            events, usage = await client.get_odds("americanfootball_nfl")

            assert len(events) == 1
            assert events[0].home_team == "Chiefs"
            assert usage["remaining"] == "499"
            mock_save_usage.assert_called_once_with(1, 499)
            await client.close()


# ═══════════════════════════════════════════════════════════════════════
# Scheduler — _scheduler_loop and start/stop with running loop
# ═══════════════════════════════════════════════════════════════════════

class TestSchedulerLoop:
    """Integration tests for _scheduler_loop."""

    @pytest.mark.asyncio
    async def test_loop_calls_refresh_then_sleeps(self):
        """_scheduler_loop calls refresh_odds then sleeps, and can be cancelled."""
        call_count = 0
        original_refresh = scheduler_module.refresh_odds

        async def mock_refresh():
            nonlocal call_count
            call_count += 1
            return RefreshResult()

        with (
            patch.object(scheduler_module, "refresh_odds", side_effect=mock_refresh),
            patch("app.scheduler.settings") as mock_s,
        ):
            mock_s.REFRESH_INTERVAL = 0.05  # 50ms for fast test

            task = asyncio.create_task(scheduler_module._scheduler_loop())
            await asyncio.sleep(0.15)  # Let it run ~2-3 iterations
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

            assert call_count >= 2

    @pytest.mark.asyncio
    async def test_loop_handles_exception_and_continues(self):
        """_scheduler_loop catches exceptions and keeps running."""
        call_count = 0

        async def failing_refresh():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            return RefreshResult()

        with (
            patch.object(scheduler_module, "refresh_odds", side_effect=failing_refresh),
            patch("app.scheduler.settings") as mock_s,
        ):
            mock_s.REFRESH_INTERVAL = 0.05

            task = asyncio.create_task(scheduler_module._scheduler_loop())
            await asyncio.sleep(0.2)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

            # Should have been called at least twice (error + recovery)
            assert call_count >= 2


class TestStartSchedulerWithLoop:
    """Integration tests for start_scheduler with a running event loop."""

    @pytest.mark.asyncio
    async def test_start_creates_task_and_stop_cancels(self):
        """start_scheduler creates a background task; stop_scheduler cancels it."""
        with (
            patch("app.scheduler.settings") as mock_s,
            patch.object(scheduler_module, "refresh_odds", new_callable=AsyncMock, return_value=RefreshResult()),
        ):
            mock_s.REFRESH_INTERVAL = 60
            mock_s.has_api_key = True

            scheduler_module._refresh_task = None
            scheduler_module.start_scheduler()

            assert scheduler_module._refresh_task is not None
            assert not scheduler_module._refresh_task.done()

            scheduler_module.stop_scheduler()
            assert scheduler_module._refresh_task is None

    @pytest.mark.asyncio
    async def test_start_scheduler_disabled_no_key(self):
        """start_scheduler doesn't create a task without API key."""
        with patch("app.scheduler.settings") as mock_s:
            mock_s.REFRESH_INTERVAL = 60
            mock_s.has_api_key = False

            scheduler_module._refresh_task = None
            scheduler_module.start_scheduler()

            assert scheduler_module._refresh_task is None


# ═══════════════════════════════════════════════════════════════════════
# FastAPI lifespan — startup and shutdown paths
# ═══════════════════════════════════════════════════════════════════════

class TestLifespanWithApiKey:
    """Integration tests for the lifespan context manager with API key set."""

    def test_lifespan_with_api_key_calls_refresh_and_scheduler(self):
        """When has_api_key=True, lifespan runs initial refresh and starts scheduler."""
        from app.main import app

        with (
            patch("app.main.init_db") as mock_init,
            patch("app.main.refresh_odds", new_callable=AsyncMock, return_value=RefreshResult()) as mock_refresh,
            patch("app.main.start_scheduler") as mock_start,
            patch("app.main.stop_scheduler") as mock_stop,
            patch("app.main.settings") as mock_s,
        ):
            mock_s.has_api_key = True
            mock_s.DB_PATH = ":memory:"

            with TestClient(app):
                mock_init.assert_called_once()
                mock_refresh.assert_awaited_once()
                mock_start.assert_called_once()

            # After exiting, stop should have been called
            mock_stop.assert_called_once()

    def test_lifespan_without_api_key_skips_refresh(self):
        """When has_api_key=False, lifespan skips refresh and scheduler."""
        from app.main import app

        with (
            patch("app.main.init_db"),
            patch("app.main.refresh_odds", new_callable=AsyncMock) as mock_refresh,
            patch("app.main.start_scheduler") as mock_start,
            patch("app.main.stop_scheduler"),
            patch("app.main.settings") as mock_s,
        ):
            mock_s.has_api_key = False
            mock_s.DB_PATH = ":memory:"

            with TestClient(app):
                mock_refresh.assert_not_awaited()
                mock_start.assert_not_called()


class TestFullApiRoundTrip:
    """End-to-end API round-trip: write data → read via endpoints."""

    def test_arbitrage_write_then_read(self, tmp_path):
        """Save arbs to DB, then read via /api/arbitrage."""
        from app.main import app
        from app.database import init_db, save_arbitrage

        db_path = str(tmp_path / "integration.db")

        with (
            patch("app.main.init_db"),
            patch("app.main.refresh_odds", new_callable=AsyncMock),
            patch("app.main.start_scheduler"),
            patch("app.main.stop_scheduler"),
            patch("app.main.settings") as mock_main_s,
            patch("app.database.settings") as mock_db_s,
        ):
            mock_main_s.has_api_key = False
            mock_main_s.DB_PATH = db_path
            mock_main_s.SPORT_KEYS = {"NFL": "nfl"}
            mock_main_s.MARKETS = "h2h"
            mock_main_s.REGIONS = "us"
            mock_main_s.MIN_PROFIT_PCT = 0.0
            mock_main_s.REFRESH_INTERVAL = 300

            mock_db_s.DB_PATH = db_path

            # Initialize database and insert test data
            init_db()
            legs = json.dumps([{"outcome": "A", "bookmaker": "B1", "price": 150, "implied_prob": 0.4, "stake_pct": 47}])
            save_arbitrage([
                {
                    "sport_key": "nfl",
                    "event_id": "e1",
                    "event_name": "A @ B",
                    "home_team": "B",
                    "away_team": "A",
                    "commence_time": "2026-01-01T00:00:00Z",
                    "market": "h2h",
                    "profit_pct": 2.5,
                    "legs": legs,
                    "total_implied_prob": 0.975,
                    "detected_at": "2026-01-01T12:00:00Z",
                }
            ])

            with TestClient(app) as client:
                resp = client.get("/api/arbitrage")
                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 1
                assert data["arbitrage"][0]["profit_pct"] == 2.5
                assert isinstance(data["arbitrage"][0]["legs"], list)

    def test_odds_write_then_read(self, tmp_path):
        """Save odds to DB, then read via /api/odds."""
        from app.main import app
        from app.database import init_db, save_odds

        db_path = str(tmp_path / "integration_odds.db")

        with (
            patch("app.main.init_db"),
            patch("app.main.refresh_odds", new_callable=AsyncMock),
            patch("app.main.start_scheduler"),
            patch("app.main.stop_scheduler"),
            patch("app.main.settings") as mock_main_s,
            patch("app.database.settings") as mock_db_s,
        ):
            mock_main_s.has_api_key = False
            mock_main_s.DB_PATH = db_path
            mock_main_s.SPORT_KEYS = {"NFL": "americanfootball_nfl"}
            mock_main_s.MARKETS = "h2h"
            mock_main_s.REGIONS = "us"
            mock_main_s.MIN_PROFIT_PCT = 0.0
            mock_main_s.REFRESH_INTERVAL = 300

            mock_db_s.DB_PATH = db_path

            init_db()
            save_odds([
                {
                    "sport_key": "americanfootball_nfl",
                    "event_id": "e1",
                    "event_name": "Bills @ Chiefs",
                    "home_team": "Chiefs",
                    "away_team": "Bills",
                    "commence_time": "2026-02-16T18:00:00Z",
                    "bookmaker": "FanDuel",
                    "market": "h2h",
                    "outcome_name": "Chiefs",
                    "price": -150,
                    "point": None,
                    "fetched_at": "2026-02-16T12:00:00Z",
                }
            ])

            with TestClient(app) as client:
                resp = client.get("/api/odds?sport=NFL")
                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] >= 1
                assert data["odds"][0]["bookmaker"] == "FanDuel"

    def test_status_reflects_last_refresh(self):
        """GET /api/status reflects the last refresh result."""
        from app.main import app

        result = RefreshResult(events_fetched=42, arbitrage_found=3)

        with (
            patch("app.main.init_db"),
            patch("app.main.refresh_odds", new_callable=AsyncMock),
            patch("app.main.start_scheduler"),
            patch("app.main.stop_scheduler"),
            patch("app.main.settings") as mock_s,
            patch("app.main.get_last_result", return_value=result),
            patch("app.main.get_api_usage", return_value={"requests_used": 8, "requests_remaining": 492}),
        ):
            mock_s.has_api_key = True
            mock_s.DB_PATH = ":memory:"
            mock_s.REFRESH_INTERVAL = 300
            mock_s.SPORT_KEYS = {"NFL": "nfl"}
            mock_s.MARKETS = "h2h"
            mock_s.REGIONS = "us"
            mock_s.MIN_PROFIT_PCT = 0.0

            with TestClient(app) as client:
                resp = client.get("/api/status")
                data = resp.json()
                assert data["last_refresh"]["events_fetched"] == 42
                assert data["last_refresh"]["arbitrage_found"] == 3
                assert data["api_usage"]["requests_remaining"] == 492

    def test_refresh_endpoint_triggers_full_cycle(self):
        """POST /api/refresh triggers refresh_odds and returns result."""
        from app.main import app

        mock_result = RefreshResult(events_fetched=10, arbitrage_found=1)

        with (
            patch("app.main.init_db"),
            patch("app.main.start_scheduler"),
            patch("app.main.stop_scheduler"),
            patch("app.main.settings") as mock_s,
            patch("app.main.refresh_odds", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_s.has_api_key = False
            mock_s.DB_PATH = ":memory:"

            with TestClient(app) as client:
                resp = client.post("/api/refresh")
                assert resp.status_code == 200
                data = resp.json()
                assert data["events_fetched"] == 10
                assert data["arbitrage_found"] == 1
