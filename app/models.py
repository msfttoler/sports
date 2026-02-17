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


# ═══════════════════════════════════════════════════════════════════════
# Prediction Models
# ═══════════════════════════════════════════════════════════════════════

class TeamRecord(BaseModel):
    """Season record for a team."""
    team: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    home_wins: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_losses: int = 0
    streak: int = 0  # positive = win streak, negative = loss streak
    last_5: list[str] = Field(default_factory=list)  # ["W","L","W","W","L"]
    sport_key: str = ""
    season: str = ""

    @property
    def win_pct(self) -> float:
        total = self.wins + self.losses + self.ties
        return self.wins / total if total > 0 else 0.0

    @property
    def ppg(self) -> float:
        total = self.wins + self.losses + self.ties
        return self.points_for / total if total > 0 else 0.0

    @property
    def opp_ppg(self) -> float:
        total = self.wins + self.losses + self.ties
        return self.points_against / total if total > 0 else 0.0

    @property
    def point_diff(self) -> float:
        return self.ppg - self.opp_ppg

    @property
    def home_win_pct(self) -> float:
        total = self.home_wins + self.home_losses
        return self.home_wins / total if total > 0 else 0.5

    @property
    def away_win_pct(self) -> float:
        total = self.away_wins + self.away_losses
        return self.away_wins / total if total > 0 else 0.5

    @property
    def last_5_win_pct(self) -> float:
        if not self.last_5:
            return 0.5
        return sum(1 for r in self.last_5 if r == "W") / len(self.last_5)


class GamePrediction(BaseModel):
    """AI-generated prediction for a single game."""
    event_id: str
    sport_key: str
    home_team: str
    away_team: str
    commence_time: str
    predicted_winner: str
    home_win_prob: float  # 0.0 – 1.0
    away_win_prob: float  # 0.0 – 1.0
    confidence: float  # 0.0 – 1.0 (how sure the model is)
    confidence_label: str  # "lock", "strong", "lean", "toss-up"
    spread_prediction: float | None = None  # predicted point spread (home perspective)
    total_prediction: float | None = None  # predicted total points
    # Spread coverage analysis
    book_spread: float | None = None  # bookmaker spread line (home perspective, e.g. -3.5)
    cover_prob: float | None = None  # probability home team covers the book spread
    cover_side: str | None = None  # "home" or "away" — which side to bet
    cover_confidence: float | None = None  # 0.0 – 1.0
    cover_label: str | None = None  # "lock", "strong", "lean", "toss-up", "fade"
    cover_reasoning: str | None = None
    features: dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""
    model_version: str = "v1.0"
    predicted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ValueBet(BaseModel):
    """A bet where our model disagrees with the books — potential edge."""
    event_id: str
    sport_key: str
    event_name: str
    commence_time: str
    team: str  # team we think has value
    our_prob: float  # our model's win probability
    book_implied_prob: float  # bookmaker's implied probability
    best_price: int  # best American odds available
    best_bookmaker: str
    edge_pct: float  # our_prob - book_implied_prob (positive = value)
    confidence: float
    confidence_label: str
    kelly_fraction: float  # Kelly criterion suggested stake %
    predicted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
