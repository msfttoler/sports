"""
Configuration management for the Sports Arbitrage Finder.
Loads settings from .env file and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # The Odds API (https://the-odds-api.com)
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"

    # Sports to track (The Odds API sport keys)
    SPORT_KEYS: dict[str, str] = {
        "NFL": "americanfootball_nfl",
        "NBA": "basketball_nba",
        "MLB": "baseball_mlb",
        "NHL": "icehockey_nhl",
        "NCAAF": "americanfootball_ncaaf",
        "NCAAM": "basketball_ncaab",
        "EPL": "soccer_epl",
        "LA LIGA": "soccer_spain_la_liga",
        "SERIE A": "soccer_italy_serie_a",
        "UCL": "soccer_uefa_champs_league",
    }

    # Odds format: "american" | "decimal" | "iso"
    ODDS_FORMAT: str = os.getenv("ODDS_FORMAT", "american")

    # Markets to fetch: h2h (moneyline), spreads, totals
    MARKETS: str = os.getenv("MARKETS", "h2h")

    # Regions determine which bookmakers appear: us, us2, uk, eu, au
    REGIONS: str = os.getenv("REGIONS", "us,us2")

    # Minimum arbitrage profit % to surface (e.g. 0.5 means 0.5%)
    MIN_PROFIT_PCT: float = float(os.getenv("MIN_PROFIT_PCT", "0.0"))

    # Auto-refresh interval in seconds (0 = manual only, 14400 = 4 hours)
    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "14400"))

    # SQLite database path
    DB_PATH: str = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "arbitrage.db"))

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def has_api_key(self) -> bool:
        return bool(self.ODDS_API_KEY)


settings = Settings()
