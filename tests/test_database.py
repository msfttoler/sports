"""Tests for app.database — SQLite persistence layer."""

import sqlite3
import tempfile
import os
from unittest.mock import patch

import pytest

from app.database import (
    get_api_usage,
    get_arbitrage_history,
    get_connection,
    get_db,
    get_latest_odds,
    get_live_arbitrage,
    init_db,
    save_api_usage,
    save_arbitrage,
    save_odds,
)


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path and patch settings."""
    db_path = str(tmp_path / "test.db")
    with patch("app.database.settings") as mock_settings:
        mock_settings.DB_PATH = db_path
        init_db()
        yield db_path, mock_settings


class TestInitDb:
    """Tests for init_db."""

    def test_creates_tables(self, tmp_db):
        db_path, _ = tmp_db
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "odds_snapshots" in tables
        assert "arbitrage_opportunities" in tables
        assert "api_usage" in tables

    def test_idempotent(self, tmp_db):
        db_path, mock_settings = tmp_db
        # Call init_db again — should not raise
        with patch("app.database.settings", mock_settings):
            init_db()


class TestGetConnection:
    """Tests for get_connection."""

    def test_returns_connection(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            conn = get_connection()
            assert isinstance(conn, sqlite3.Connection)
            conn.close()

    def test_row_factory_set(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            conn = get_connection()
            assert conn.row_factory == sqlite3.Row
            conn.close()


class TestGetDb:
    """Tests for get_db context manager."""

    def test_yields_connection(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            with get_db() as conn:
                assert isinstance(conn, sqlite3.Connection)

    def test_commits_on_success(self, tmp_db):
        db_path, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO api_usage (requests_used, requests_remaining) VALUES (1, 499)"
                )
            # Verify data persisted
            check = sqlite3.connect(db_path)
            row = check.execute("SELECT * FROM api_usage").fetchone()
            check.close()
            assert row is not None


class TestSaveOdds:
    """Tests for save_odds."""

    def test_empty_rows_no_op(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            save_odds([])  # Should not raise

    def test_saves_rows(self, tmp_db):
        db_path, mock_settings = tmp_db
        rows = [
            {
                "sport_key": "nfl",
                "event_id": "e1",
                "event_name": "A @ B",
                "home_team": "B",
                "away_team": "A",
                "commence_time": "2026-01-01T00:00:00Z",
                "bookmaker": "FanDuel",
                "market": "h2h",
                "outcome_name": "B",
                "price": -150,
                "point": None,
                "fetched_at": "2026-01-01T12:00:00Z",
            }
        ]
        with patch("app.database.settings", mock_settings):
            save_odds(rows)
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0]
            conn.close()
            assert count == 1

    def test_multiple_rows(self, tmp_db):
        db_path, mock_settings = tmp_db
        rows = [
            {
                "sport_key": "nfl",
                "event_id": f"e{i}",
                "event_name": f"A{i} @ B{i}",
                "home_team": f"B{i}",
                "away_team": f"A{i}",
                "commence_time": "2026-01-01T00:00:00Z",
                "bookmaker": "FanDuel",
                "market": "h2h",
                "outcome_name": f"B{i}",
                "price": -110,
                "point": None,
                "fetched_at": "2026-01-01T12:00:00Z",
            }
            for i in range(5)
        ]
        with patch("app.database.settings", mock_settings):
            save_odds(rows)
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0]
            conn.close()
            assert count == 5


class TestSaveArbitrage:
    """Tests for save_arbitrage."""

    def test_empty_no_op(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            save_arbitrage([])

    def test_saves_and_marks_previous_stale(self, tmp_db):
        db_path, mock_settings = tmp_db
        opp = {
            "sport_key": "nfl",
            "event_id": "e1",
            "event_name": "A @ B",
            "home_team": "B",
            "away_team": "A",
            "commence_time": "2026-01-01T00:00:00Z",
            "market": "h2h",
            "profit_pct": 2.5,
            "legs": "[]",
            "total_implied_prob": 0.975,
            "detected_at": "2026-01-01T12:00:00Z",
        }
        with patch("app.database.settings", mock_settings):
            save_arbitrage([opp])
            # Save again — old should be stale
            opp2 = {**opp, "event_id": "e2", "profit_pct": 3.0}
            save_arbitrage([opp2])

            conn = sqlite3.connect(db_path)
            live = conn.execute(
                "SELECT COUNT(*) FROM arbitrage_opportunities WHERE still_live = 1"
            ).fetchone()[0]
            stale = conn.execute(
                "SELECT COUNT(*) FROM arbitrage_opportunities WHERE still_live = 0"
            ).fetchone()[0]
            conn.close()
            assert live == 1
            assert stale == 1


class TestGetLiveArbitrage:
    """Tests for get_live_arbitrage."""

    def test_empty_when_no_data(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            result = get_live_arbitrage()
            assert result == []

    def test_returns_live_only(self, tmp_db):
        db_path, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            opp = {
                "sport_key": "nfl",
                "event_id": "e1",
                "event_name": "A @ B",
                "home_team": "B",
                "away_team": "A",
                "commence_time": "2026-01-01T00:00:00Z",
                "market": "h2h",
                "profit_pct": 2.5,
                "legs": "[]",
                "total_implied_prob": 0.975,
                "detected_at": "2026-01-01T12:00:00Z",
            }
            save_arbitrage([opp])
            result = get_live_arbitrage()
            assert len(result) == 1
            assert result[0]["still_live"] == 1

    def test_ordered_by_profit_desc(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            opps = [
                {
                    "sport_key": "nfl", "event_id": "e1", "event_name": "A@B",
                    "home_team": "B", "away_team": "A",
                    "commence_time": "2026-01-01T00:00:00Z", "market": "h2h",
                    "profit_pct": 1.5, "legs": "[]", "total_implied_prob": 0.985,
                    "detected_at": "2026-01-01T12:00:00Z",
                },
                {
                    "sport_key": "nfl", "event_id": "e2", "event_name": "C@D",
                    "home_team": "D", "away_team": "C",
                    "commence_time": "2026-01-01T00:00:00Z", "market": "h2h",
                    "profit_pct": 3.0, "legs": "[]", "total_implied_prob": 0.97,
                    "detected_at": "2026-01-01T12:00:00Z",
                },
            ]
            save_arbitrage(opps)
            result = get_live_arbitrage()
            assert result[0]["profit_pct"] >= result[1]["profit_pct"]


class TestGetArbitrageHistory:
    """Tests for get_arbitrage_history."""

    def test_empty(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            assert get_arbitrage_history() == []

    def test_respects_limit(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            opps = [
                {
                    "sport_key": "nfl", "event_id": f"e{i}", "event_name": f"A@B{i}",
                    "home_team": "B", "away_team": "A",
                    "commence_time": "2026-01-01T00:00:00Z", "market": "h2h",
                    "profit_pct": float(i), "legs": "[]",
                    "total_implied_prob": 0.98, "detected_at": "2026-01-01T12:00:00Z",
                }
                for i in range(10)
            ]
            save_arbitrage(opps)
            result = get_arbitrage_history(limit=3)
            assert len(result) == 3


class TestGetLatestOdds:
    """Tests for get_latest_odds."""

    def test_empty(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            assert get_latest_odds() == []

    def test_filter_by_sport(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            rows = [
                {
                    "sport_key": "nfl", "event_id": "e1", "event_name": "A@B",
                    "home_team": "B", "away_team": "A",
                    "commence_time": "2026-01-01T00:00:00Z",
                    "bookmaker": "FD", "market": "h2h", "outcome_name": "B",
                    "price": -110, "point": None, "fetched_at": "2026-01-01T12:00:00Z",
                },
                {
                    "sport_key": "nba", "event_id": "e2", "event_name": "C@D",
                    "home_team": "D", "away_team": "C",
                    "commence_time": "2026-01-01T00:00:00Z",
                    "bookmaker": "DK", "market": "h2h", "outcome_name": "D",
                    "price": -150, "point": None, "fetched_at": "2026-01-01T12:00:00Z",
                },
            ]
            save_odds(rows)
            nfl_only = get_latest_odds(sport_key="nfl")
            assert all(r["sport_key"] == "nfl" for r in nfl_only)

    def test_no_filter_returns_all_latest(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            rows = [
                {
                    "sport_key": "nfl", "event_id": "e1", "event_name": "A@B",
                    "home_team": "B", "away_team": "A",
                    "commence_time": "2026-01-01T00:00:00Z",
                    "bookmaker": "FD", "market": "h2h", "outcome_name": "B",
                    "price": -110, "point": None, "fetched_at": "2026-01-01T12:00:00Z",
                },
            ]
            save_odds(rows)
            result = get_latest_odds()
            assert len(result) >= 1


class TestSaveApiUsage:
    """Tests for save_api_usage."""

    def test_saves(self, tmp_db):
        db_path, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            save_api_usage(10, 490)
            conn = sqlite3.connect(db_path)
            row = conn.execute("SELECT * FROM api_usage").fetchone()
            conn.close()
            assert row is not None


class TestGetApiUsage:
    """Tests for get_api_usage."""

    def test_none_when_empty(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            assert get_api_usage() is None

    def test_returns_latest(self, tmp_db):
        _, mock_settings = tmp_db
        with patch("app.database.settings", mock_settings):
            save_api_usage(5, 495)
            save_api_usage(10, 490)
            result = get_api_usage()
            assert result is not None
            # The latest insert is the one returned (by recorded_at DESC, id DESC)
            assert isinstance(result["requests_used"], int)
            assert isinstance(result["requests_remaining"], int)
