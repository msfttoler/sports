"""Tests for app.scheduler — background refresh loop."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import RefreshResult
from app.scheduler import (
    _last_result,
    get_last_result,
    refresh_odds,
    start_scheduler,
    stop_scheduler,
)
import app.scheduler as scheduler_module


class TestRefreshOdds:
    """Tests for refresh_odds."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_error(self):
        with patch("app.scheduler.settings") as mock_s:
            mock_s.has_api_key = False
            result = await refresh_odds()
            assert isinstance(result, RefreshResult)
            assert len(result.errors) > 0
            assert "ODDS_API_KEY" in result.errors[0]

    @pytest.mark.asyncio
    async def test_successful_refresh(self):
        mock_client = AsyncMock()
        mock_client.fetch_all_sports.return_value = ([], {"remaining": "495"})
        mock_client.persist_events = MagicMock()
        mock_client.close = AsyncMock()

        with (
            patch("app.scheduler.settings") as mock_s,
            patch("app.scheduler.OddsClient", return_value=mock_client),
            patch("app.scheduler.detect_arbitrage", return_value=[]),
        ):
            mock_s.has_api_key = True
            mock_s.SPORT_KEYS = {"NFL": "nfl"}

            result = await refresh_odds()
            assert isinstance(result, RefreshResult)
            assert result.events_fetched == 0
            assert result.arbitrage_found == 0
            assert result.api_requests_remaining == 495
            mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_during_fetch(self):
        mock_client = AsyncMock()
        mock_client.fetch_all_sports.side_effect = Exception("API down")
        mock_client.close = AsyncMock()

        with (
            patch("app.scheduler.settings") as mock_s,
            patch("app.scheduler.OddsClient", return_value=mock_client),
        ):
            mock_s.has_api_key = True

            result = await refresh_odds()
            assert len(result.errors) > 0
            assert "API down" in result.errors[0]
            mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sets_last_result(self):
        with (
            patch("app.scheduler.settings") as mock_s,
            patch("app.scheduler.OddsClient") as MockClient,
            patch("app.scheduler.detect_arbitrage", return_value=[]),
        ):
            mock_s.has_api_key = True
            mock_s.SPORT_KEYS = {"NFL": "nfl"}
            mock_instance = AsyncMock()
            mock_instance.fetch_all_sports.return_value = ([], {})
            mock_instance.persist_events = MagicMock()
            MockClient.return_value = mock_instance

            result = await refresh_odds()
            assert get_last_result() is result

    @pytest.mark.asyncio
    async def test_usage_none_remaining(self):
        mock_client = AsyncMock()
        mock_client.fetch_all_sports.return_value = ([], {"remaining": None})
        mock_client.persist_events = MagicMock()
        mock_client.close = AsyncMock()

        with (
            patch("app.scheduler.settings") as mock_s,
            patch("app.scheduler.OddsClient", return_value=mock_client),
            patch("app.scheduler.detect_arbitrage", return_value=[]),
        ):
            mock_s.has_api_key = True
            mock_s.SPORT_KEYS = {"NFL": "nfl"}

            result = await refresh_odds()
            assert result.api_requests_remaining is None


class TestGetLastResult:
    """Tests for get_last_result."""

    def test_initially_none(self):
        scheduler_module._last_result = None
        assert get_last_result() is None

    def test_returns_stored_result(self):
        r = RefreshResult(events_fetched=5)
        scheduler_module._last_result = r
        assert get_last_result() is r
        scheduler_module._last_result = None  # cleanup


class TestStartScheduler:
    """Tests for start_scheduler."""

    def test_disabled_when_no_api_key(self):
        with patch("app.scheduler.settings") as mock_s:
            mock_s.has_api_key = False
            mock_s.REFRESH_INTERVAL = 300
            start_scheduler()
            assert scheduler_module._refresh_task is None

    def test_disabled_when_interval_zero(self):
        with patch("app.scheduler.settings") as mock_s:
            mock_s.has_api_key = True
            mock_s.REFRESH_INTERVAL = 0
            start_scheduler()
            assert scheduler_module._refresh_task is None


class TestStopScheduler:
    """Tests for stop_scheduler."""

    def test_stop_when_no_task(self):
        scheduler_module._refresh_task = None
        stop_scheduler()  # Should not raise
        assert scheduler_module._refresh_task is None

    def test_stop_cancels_task(self):
        mock_task = MagicMock()
        scheduler_module._refresh_task = mock_task
        stop_scheduler()
        mock_task.cancel.assert_called_once()
        assert scheduler_module._refresh_task is None
