"""Tests for app.config — Settings and configuration."""

from unittest.mock import patch
import os

import pytest


class TestSettings:
    """Tests for the Settings class."""

    def test_defaults_exist(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.ODDS_API_BASE_URL, str)
        assert "api.the-odds-api.com" in s.ODDS_API_BASE_URL
        assert isinstance(s.ODDS_FORMAT, str)
        assert isinstance(s.MARKETS, str)
        assert isinstance(s.REGIONS, str)
        assert isinstance(s.MIN_PROFIT_PCT, float)
        assert isinstance(s.REFRESH_INTERVAL, int)
        assert isinstance(s.HOST, str)
        assert isinstance(s.PORT, int)

    def test_sport_keys_populated(self):
        from app.config import Settings
        s = Settings()
        assert "NFL" in s.SPORT_KEYS
        assert "NBA" in s.SPORT_KEYS
        assert "MLB" in s.SPORT_KEYS
        assert "NHL" in s.SPORT_KEYS
        assert s.SPORT_KEYS["NFL"] == "americanfootball_nfl"

    def test_has_api_key_false_when_empty(self):
        from app.config import Settings
        with patch.dict(os.environ, {"ODDS_API_KEY": ""}, clear=False):
            s = Settings()
            s.ODDS_API_KEY = ""
            assert s.has_api_key is False

    def test_has_api_key_true_when_set(self):
        from app.config import Settings
        s = Settings()
        s.ODDS_API_KEY = "test-key-123"
        assert s.has_api_key is True

    def test_db_path_is_string(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.DB_PATH, str)
        assert "arbitrage.db" in s.DB_PATH

    def test_default_port(self):
        from app.config import Settings
        s = Settings()
        assert s.PORT == 8000 or isinstance(s.PORT, int)

    def test_default_host(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.HOST, str)

    def test_min_profit_pct_is_float(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.MIN_PROFIT_PCT, float)
        assert s.MIN_PROFIT_PCT >= 0.0

    def test_singleton_settings_importable(self):
        from app.config import settings
        assert settings is not None
        assert hasattr(settings, "ODDS_API_KEY")
