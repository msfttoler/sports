"""Tests for app.main — FastAPI routes and endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models import RefreshResult


@pytest.fixture
def client():
    """Create a test client with lifespan disabled."""
    from app.main import app
    # Use TestClient which handles lifespan
    with patch("app.main.init_db"):
        with patch("app.main.refresh_odds", new_callable=AsyncMock):
            with patch("app.main.start_scheduler"):
                with patch("app.main.stop_scheduler"):
                    with patch("app.main.settings") as mock_s:
                        mock_s.has_api_key = False
                        mock_s.DB_PATH = ":memory:"
                        mock_s.REFRESH_INTERVAL = 300
                        mock_s.SPORT_KEYS = {"NFL": "nfl", "NBA": "nba"}
                        mock_s.MARKETS = "h2h"
                        mock_s.REGIONS = "us,us2"
                        mock_s.MIN_PROFIT_PCT = 0.0
                        with TestClient(app) as c:
                            yield c


class TestDashboard:
    """Tests for the dashboard endpoint."""

    def test_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Sports" in resp.text or "Arbitrage" in resp.text


class TestApiArbitrage:
    """Tests for GET /api/arbitrage."""

    @patch("app.main.get_live_arbitrage", return_value=[])
    def test_empty_arbs(self, mock_get, client):
        resp = client.get("/api/arbitrage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["arbitrage"] == []
        assert "timestamp" in data

    @patch("app.main.get_live_arbitrage")
    def test_parses_legs_json(self, mock_get, client):
        mock_get.return_value = [
            {
                "id": 1,
                "legs": json.dumps([{"outcome": "A", "bookmaker": "B1", "price": 150}]),
                "profit_pct": 2.0,
            }
        ]
        resp = client.get("/api/arbitrage")
        data = resp.json()
        assert isinstance(data["arbitrage"][0]["legs"], list)
        assert data["arbitrage"][0]["legs"][0]["outcome"] == "A"

    @patch("app.main.get_live_arbitrage")
    def test_legs_already_parsed(self, mock_get, client):
        mock_get.return_value = [
            {
                "id": 1,
                "legs": [{"outcome": "A"}],
                "profit_pct": 2.0,
            }
        ]
        resp = client.get("/api/arbitrage")
        data = resp.json()
        assert data["arbitrage"][0]["legs"][0]["outcome"] == "A"


class TestApiArbitrageHistory:
    """Tests for GET /api/arbitrage/history."""

    @patch("app.main.get_arbitrage_history", return_value=[])
    def test_empty(self, mock_get, client):
        resp = client.get("/api/arbitrage/history")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @patch("app.main.get_arbitrage_history", return_value=[])
    def test_custom_limit(self, mock_get, client):
        resp = client.get("/api/arbitrage/history?limit=10")
        assert resp.status_code == 200
        mock_get.assert_called_once_with(10)

    def test_invalid_limit_below_range(self, client):
        resp = client.get("/api/arbitrage/history?limit=0")
        assert resp.status_code == 422

    def test_invalid_limit_above_range(self, client):
        resp = client.get("/api/arbitrage/history?limit=501")
        assert resp.status_code == 422


class TestApiOdds:
    """Tests for GET /api/odds."""

    @patch("app.main.get_latest_odds", return_value=[])
    def test_no_filter(self, mock_get, client):
        resp = client.get("/api/odds")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        mock_get.assert_called_once_with(None)

    @patch("app.main.get_latest_odds", return_value=[])
    @patch("app.main.settings")
    def test_sport_filter(self, mock_settings, mock_get, client):
        mock_settings.SPORT_KEYS = {"NFL": "americanfootball_nfl"}
        resp = client.get("/api/odds?sport=NFL")
        assert resp.status_code == 200


class TestApiRefresh:
    """Tests for POST /api/refresh."""

    @patch("app.main.refresh_odds", new_callable=AsyncMock)
    def test_returns_result(self, mock_refresh, client):
        mock_refresh.return_value = RefreshResult(events_fetched=5, arbitrage_found=1)
        resp = client.post("/api/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events_fetched"] == 5
        assert data["arbitrage_found"] == 1


class TestApiStatus:
    """Tests for GET /api/status."""

    @patch("app.main.get_api_usage", return_value=None)
    @patch("app.main.get_last_result", return_value=None)
    def test_status_no_data(self, mock_last, mock_usage, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key_configured" in data
        assert "sports_tracked" in data
        assert data["last_refresh"] is None

    @patch("app.main.get_api_usage", return_value={"requests_used": 10, "requests_remaining": 490})
    @patch("app.main.get_last_result")
    def test_status_with_data(self, mock_last, mock_usage, client):
        mock_last.return_value = RefreshResult(events_fetched=50)
        resp = client.get("/api/status")
        data = resp.json()
        assert data["api_usage"]["requests_remaining"] == 490


class TestApiSports:
    """Tests for GET /api/sports."""

    def test_returns_sports(self, client):
        resp = client.get("/api/sports")
        assert resp.status_code == 200
        data = resp.json()
        assert "sports" in data
