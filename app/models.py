"""
Pydantic models for the Sports Arbitrage Finder.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class OddsOutcome(BaseModel):
    """A single outcome line from a bookmaker."""
    name: str
    price: int  # American odds
    point: float | None = None  # Spread / total line


class BookmakerOdds(BaseModel):
    """Odds offered by one bookmaker for one market on one event."""
    bookmaker_key: str
    bookmaker_title: str
    market: str
    outcomes: list[OddsOutcome]
    last_update: str | None = None


class Event(BaseModel):
    """A sporting event with odds from multiple bookmakers."""
    id: str
    sport_key: str
    sport_title: str
    home_team: str
    away_team: str
    commence_time: str
    bookmakers: list[BookmakerOdds] = Field(default_factory=list)


class ArbLeg(BaseModel):
    """One leg of an arbitrage opportunity."""
    outcome: str
    bookmaker: str
    price: int  # American odds
    implied_prob: float
    stake_pct: float  # Percentage of total bankroll to wager on this leg


class ArbitrageOpportunity(BaseModel):
    """A detected arbitrage opportunity."""
    sport_key: str
    event_id: str
    event_name: str
    home_team: str
    away_team: str
    commence_time: str
    market: str
    profit_pct: float
    total_implied_prob: float
    legs: list[ArbLeg]
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RefreshResult(BaseModel):
    """Result of an odds refresh operation."""
    events_fetched: int = 0
    arbitrage_found: int = 0
    sports_checked: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    api_requests_remaining: int | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApiUsage(BaseModel):
    """API usage tracking."""
    requests_used: int | None = None
    requests_remaining: int | None = None
    recorded_at: str | None = None
