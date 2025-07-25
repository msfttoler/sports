"""
Data models for the Sports Prediction System.
Defines Pydantic models for sports data, predictions, and ML features.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SportType(str, Enum):
    """Supported sports types."""
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"


class GameStatus(str, Enum):
    """Game status enumeration."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class Team(BaseModel):
    """Team information model."""
    id: str = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Team name")
    city: str = Field(..., description="Team city")
    abbreviation: str = Field(..., description="Team abbreviation")
    sport: SportType = Field(..., description="Sport type")
    conference: Optional[str] = Field(None, description="Conference/Division")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional team metadata")


class GameScore(BaseModel):
    """Game score information."""
    home_score: Optional[int] = Field(None, description="Home team score")
    away_score: Optional[int] = Field(None, description="Away team score")
    period_scores: List[int] = Field(default_factory=list, description="Scores by period")
    current_period: Optional[int] = Field(None, description="Current period/quarter")


class Game(BaseModel):
    """Game information model."""
    id: str = Field(..., description="Unique game identifier")
    sport: SportType = Field(..., description="Sport type")
    home_team: Team = Field(..., description="Home team")
    away_team: Team = Field(..., description="Away team")
    scheduled_date: datetime = Field(..., description="Scheduled game date and time")
    status: GameStatus = Field(..., description="Current game status")
    score: Optional[GameScore] = Field(None, description="Game score information")
    season: str = Field(..., description="Season identifier")
    week: Optional[int] = Field(None, description="Week number (for applicable sports)")
    venue: Optional[str] = Field(None, description="Game venue")
    weather: Optional[Dict[str, Any]] = Field(None, description="Weather conditions")
    officials: List[str] = Field(default_factory=list, description="Game officials")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional game metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamStats(BaseModel):
    """Team statistics model."""
    team_id: str = Field(..., description="Team identifier")
    season: str = Field(..., description="Season identifier")
    games_played: int = Field(..., description="Number of games played")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    ties: Optional[int] = Field(0, description="Number of ties")
    points_for: float = Field(..., description="Total points scored")
    points_against: float = Field(..., description="Total points allowed")
    home_record: Dict[str, int] = Field(default_factory=dict, description="Home game record")
    away_record: Dict[str, int] = Field(default_factory=dict, description="Away game record")
    recent_form: List[str] = Field(default_factory=list, description="Recent game results (W/L)")
    advanced_stats: Dict[str, float] = Field(default_factory=dict, description="Advanced statistics")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PredictionOutcome(str, Enum):
    """Prediction outcome types."""
    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    TIE = "tie"


class GamePrediction(BaseModel):
    """Game prediction model with confidence scoring."""
    id: str = Field(..., description="Unique prediction identifier")
    game_id: str = Field(..., description="Associated game identifier")
    predicted_outcome: PredictionOutcome = Field(..., description="Predicted game outcome")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Confidence score (0-100)")
    predicted_home_score: Optional[float] = Field(None, description="Predicted home team score")
    predicted_away_score: Optional[float] = Field(None, description="Predicted away team score")
    win_probability: Dict[str, float] = Field(default_factory=dict, description="Win probabilities by team")
    model_version: str = Field(..., description="ML model version used")
    features_used: List[str] = Field(default_factory=list, description="Features used in prediction")
    prediction_reasoning: Optional[str] = Field(None, description="Human-readable prediction reasoning")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional prediction metadata")


class MLFeatures(BaseModel):
    """Machine learning features for game prediction."""
    game_id: str = Field(..., description="Associated game identifier")
    home_team_features: Dict[str, float] = Field(default_factory=dict, description="Home team features")
    away_team_features: Dict[str, float] = Field(default_factory=dict, description="Away team features")
    matchup_features: Dict[str, float] = Field(default_factory=dict, description="Head-to-head features")
    contextual_features: Dict[str, float] = Field(default_factory=dict, description="Contextual features (weather, venue, etc.)")
    historical_features: Dict[str, float] = Field(default_factory=dict, description="Historical performance features")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelMetrics(BaseModel):
    """ML model performance metrics."""
    model_version: str = Field(..., description="Model version identifier")
    sport: SportType = Field(..., description="Sport type")
    accuracy: float = Field(..., description="Model accuracy")
    precision: float = Field(..., description="Model precision")
    recall: float = Field(..., description="Model recall")
    f1_score: float = Field(..., description="F1 score")
    auc_roc: Optional[float] = Field(None, description="AUC-ROC score")
    calibration_score: Optional[float] = Field(None, description="Calibration score")
    training_samples: int = Field(..., description="Number of training samples")
    validation_samples: int = Field(..., description="Number of validation samples")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional model metadata")
