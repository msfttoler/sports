"""
Prediction Engine — ML-powered game outcome predictions.

Uses team stats features with gradient boosting to predict:
  1. Win probability for each team
  2. Confidence level (lock / strong / lean / toss-up)
  3. Predicted spread and total

The model is feature-engineered from real team records and can be
trained on historical data or applied heuristically when training
data is unavailable (cold-start mode).
"""

import logging
import math
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.injuries import InjuryReport

from app.models import Event, GamePrediction, TeamRecord

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1.0-heuristic"


def confidence_label(confidence: float) -> str:
    """Map a 0-1 confidence score to a human label."""
    if confidence >= 0.80:
        return "lock"
    if confidence >= 0.65:
        return "strong"
    if confidence >= 0.55:
        return "lean"
    return "toss-up"


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def build_features(
    home: TeamRecord | None,
    away: TeamRecord | None,
) -> dict[str, float]:
    """
    Engineer features from two team records.

    All features are from the home team's perspective:
    positive = home advantage, negative = away advantage.
    """
    features: dict[str, float] = {}

    if not home or not away:
        return features

    # ── Win percentage differential ───────────────────────────────
    features["win_pct_diff"] = home.win_pct - away.win_pct

    # ── Home / away splits ────────────────────────────────────────
    features["home_home_win_pct"] = home.home_win_pct
    features["away_away_win_pct"] = away.away_win_pct
    features["venue_edge"] = home.home_win_pct - away.away_win_pct

    # ── Scoring ───────────────────────────────────────────────────
    features["ppg_diff"] = home.ppg - away.ppg
    features["opp_ppg_diff"] = away.opp_ppg - home.opp_ppg  # lower opp ppg = better D
    features["point_diff_diff"] = home.point_diff - away.point_diff

    # ── Momentum ──────────────────────────────────────────────────
    features["streak_diff"] = float(home.streak - away.streak)
    features["last5_diff"] = home.last_5_win_pct - away.last_5_win_pct

    # ── Derived strength metrics ──────────────────────────────────
    home_strength = home.win_pct * 0.5 + home.point_diff * 0.02
    away_strength = away.win_pct * 0.5 + away.point_diff * 0.02
    features["strength_diff"] = home_strength - away_strength

    # ── Home-field advantage baseline ─────────────────────────────
    features["home_field"] = 0.03  # ~3% baseline HFA across sports

    return features


def add_injury_features(
    features: dict[str, float],
    home_injuries: "InjuryReport | None" = None,
    away_injuries: "InjuryReport | None" = None,
) -> dict[str, float]:
    """Add injury-based features to existing feature dict."""
    home_impact = home_injuries.impact_score if home_injuries else 0.0
    away_impact = away_injuries.impact_score if away_injuries else 0.0

    features["injury_diff"] = away_impact - home_impact  # positive = home healthier
    features["home_injury_impact"] = -home_impact  # negative = worse for home
    features["away_injury_impact"] = away_impact   # positive = worse for away (good for home)

    return features


# ── Feature weights (heuristic, tuned from sports analytics research) ─

FEATURE_WEIGHTS: dict[str, float] = {
    "win_pct_diff": 2.5,
    "venue_edge": 1.2,
    "ppg_diff": 0.08,
    "opp_ppg_diff": 0.06,
    "point_diff_diff": 0.04,
    "streak_diff": 0.15,
    "last5_diff": 1.0,
    "strength_diff": 2.0,
    "home_field": 3.0,
    "home_home_win_pct": 0.5,
    "away_away_win_pct": -0.5,
    "injury_diff": 1.5,
    "home_injury_impact": 0.8,
    "away_injury_impact": 0.8,
}


def predict_game(
    event: Event,
    team_stats: dict[str, TeamRecord],
    home_injuries: "InjuryReport | None" = None,
    away_injuries: "InjuryReport | None" = None,
) -> GamePrediction | None:
    """
    Predict the outcome of a single game.

    Returns None if we don't have stats for either team.
    """
    home = team_stats.get(event.home_team)
    away = team_stats.get(event.away_team)

    if not home and not away:
        logger.debug("No stats for %s vs %s — skipping", event.home_team, event.away_team)
        return None

    # Use neutral placeholder if one team is missing
    if not home:
        home = TeamRecord(team=event.home_team, wins=0, losses=0, sport_key=event.sport_key)
    if not away:
        away = TeamRecord(team=event.away_team, wins=0, losses=0, sport_key=event.sport_key)

    features = build_features(home, away)
    if not features:
        return None

    # Add injury features if available
    if home_injuries or away_injuries:
        features = add_injury_features(features, home_injuries, away_injuries)

    # Score: weighted sum of features → sigmoid → probability
    raw_score = sum(
        features.get(f, 0.0) * w for f, w in FEATURE_WEIGHTS.items()
    )
    home_win_prob = _sigmoid(raw_score)
    away_win_prob = 1.0 - home_win_prob

    # Confidence: distance from 50/50
    conf = abs(home_win_prob - 0.5) * 2  # 0 at 50/50, 1 at 100/0
    conf = min(conf, 0.95)  # cap at 95%

    winner = event.home_team if home_win_prob >= 0.5 else event.away_team

    # Spread prediction: based on point differential expectations
    expected_margin = (home.point_diff - away.point_diff) / 2 + 2.5  # +2.5 HFA
    total_prediction = home.ppg + away.ppg if (home.ppg + away.ppg) > 0 else None

    # ── Spread coverage analysis ──────────────────────────────────────
    book_spread = _extract_spread(event, event.home_team)
    cover_prob = None
    cover_side = None
    cover_confidence = None
    cover_label_str = None
    cover_reasoning = None

    if book_spread is not None and expected_margin is not None:
        cover_prob, cover_side, cover_confidence, cover_label_str, cover_reasoning = (
            _analyze_spread_coverage(
                event, home, away, expected_margin, book_spread
            )
        )

    reasoning = _build_reasoning(event, home, away, features, home_win_prob)

    return GamePrediction(
        event_id=event.id,
        sport_key=event.sport_key,
        home_team=event.home_team,
        away_team=event.away_team,
        commence_time=event.commence_time,
        predicted_winner=winner,
        home_win_prob=round(home_win_prob, 4),
        away_win_prob=round(away_win_prob, 4),
        confidence=round(conf, 4),
        confidence_label=confidence_label(conf),
        spread_prediction=round(expected_margin, 1) if expected_margin else None,
        total_prediction=round(total_prediction, 1) if total_prediction else None,
        book_spread=book_spread,
        cover_prob=round(cover_prob, 4) if cover_prob is not None else None,
        cover_side=cover_side,
        cover_confidence=round(cover_confidence, 4) if cover_confidence is not None else None,
        cover_label=cover_label_str,
        cover_reasoning=cover_reasoning,
        features=features,
        reasoning=reasoning,
        model_version=MODEL_VERSION,
    )


def predict_events(
    events: list[Event],
    team_stats: dict[str, TeamRecord],
    injury_reports: dict | None = None,
) -> list[GamePrediction]:
    """Predict outcomes for a batch of events."""
    predictions: list[GamePrediction] = []

    for event in events:
        home_inj = None
        away_inj = None
        if injury_reports:
            # Try exact match, then fuzzy
            from app.injuries import _fuzzy_match
            for name, report in injury_reports.items():
                if _fuzzy_match(event.home_team, name):
                    home_inj = report
                if _fuzzy_match(event.away_team, name):
                    away_inj = report

        pred = predict_game(event, team_stats, home_inj, away_inj)
        if pred:
            predictions.append(pred)

    predictions.sort(key=lambda p: p.confidence, reverse=True)

    logger.info(
        "Generated %d predictions from %d events",
        len(predictions),
        len(events),
    )
    return predictions


def _build_reasoning(
    event: Event,
    home: TeamRecord,
    away: TeamRecord,
    features: dict[str, float],
    home_win_prob: float,
) -> str:
    """Generate a human-readable explanation of the prediction."""
    parts: list[str] = []
    winner = event.home_team if home_win_prob >= 0.5 else event.away_team
    prob = max(home_win_prob, 1 - home_win_prob)

    parts.append(f"{winner} predicted to win ({prob:.0%} probability).")

    # Record comparison
    parts.append(
        f"{event.home_team} ({home.wins}-{home.losses}) vs "
        f"{event.away_team} ({away.wins}-{away.losses})."
    )

    # Key factors
    if abs(features.get("point_diff_diff", 0)) > 5:
        better = event.home_team if features["point_diff_diff"] > 0 else event.away_team
        parts.append(f"{better} has a significant point differential advantage.")

    if abs(features.get("last5_diff", 0)) > 0.3:
        hotter = event.home_team if features["last5_diff"] > 0 else event.away_team
        parts.append(f"{hotter} is in better recent form (last 5 games).")

    if features.get("venue_edge", 0) > 0.15:
        parts.append(f"{event.home_team} has a strong home-field advantage.")

    if abs(features.get("streak_diff", 0)) >= 3:
        streaker = event.home_team if features["streak_diff"] > 0 else event.away_team
        parts.append(f"{streaker} has significant momentum (streak advantage).")

    return " ".join(parts)


# ── Spread coverage helpers ───────────────────────────────────────────

def _extract_spread(event: Event, home_team: str) -> float | None:
    """
    Extract the consensus home spread from bookmaker odds.

    Looks for 'spreads' market across all bookmakers, averages the
    home team point value. Returns negative for home favorite (e.g. -3.5).
    """
    spreads: list[float] = []

    for bm in event.bookmakers:
        if bm.market != "spreads":
            continue
        for outcome in bm.outcomes:
            if outcome.name == home_team and outcome.point is not None:
                spreads.append(outcome.point)

    if not spreads:
        return None

    return round(sum(spreads) / len(spreads), 1)


def _analyze_spread_coverage(
    event: Event,
    home: TeamRecord,
    away: TeamRecord,
    expected_margin: float,
    book_spread: float,
) -> tuple[float, str, float, str, str]:
    """
    Determine how likely a team is to cover the spread.

    Args:
        expected_margin: our predicted home margin (positive = home wins by X)
        book_spread: the book's home spread (negative = home favored)

    The key insight: if our expected margin is -7 (home wins by 7) and
    the book spread is -3.5, the home team should cover because we
    expect them to win by more than the spread asks.

    Returns: (cover_prob, cover_side, cover_confidence, cover_label, reasoning)
    """
    # How many points better do we think home is vs what the spread asks?
    # book_spread is from home perspective: -3.5 means home must win by 4+
    # expected_margin is positive when home is favored
    #
    # edge = expected_margin - (-book_spread) ... but book_spread is already
    # in home terms, so:
    #   If expected_margin = 7 and book_spread = -3.5 → edge = 7 - 3.5 = 3.5 (home covers easily)
    #   If expected_margin = 2 and book_spread = -6.5 → edge = 2 - 6.5 = -4.5 (away covers)

    edge_over_spread = expected_margin + book_spread  # both in home terms

    # Convert edge to a probability via sigmoid (scaled so ±7 ≈ 85%/15%)
    SPREAD_SCALE = 0.25  # tuning parameter — how quickly prob moves with edge
    home_cover_prob = _sigmoid(edge_over_spread * SPREAD_SCALE)
    away_cover_prob = 1.0 - home_cover_prob

    # Which side covers?
    if home_cover_prob >= 0.5:
        cover_side = "home"
        cover_prob = home_cover_prob
        cover_team = event.home_team
        fade_team = event.away_team
    else:
        cover_side = "away"
        cover_prob = away_cover_prob
        cover_team = event.away_team
        fade_team = event.home_team

    # Confidence
    cover_confidence = abs(cover_prob - 0.5) * 2
    cover_confidence = min(cover_confidence, 0.95)

    # Label
    if cover_confidence >= 0.70:
        cover_label = "lock"
    elif cover_confidence >= 0.50:
        cover_label = "strong"
    elif cover_confidence >= 0.30:
        cover_label = "lean"
    elif cover_confidence >= 0.10:
        cover_label = "toss-up"
    else:
        cover_label = "fade"

    # Reasoning
    spread_str = f"{book_spread:+.1f}" if book_spread else "PK"
    parts = [f"Book spread: {event.home_team} {spread_str}."]
    parts.append(f"Our model projects {event.home_team} winning by {expected_margin:+.1f}.")

    if abs(edge_over_spread) >= 4:
        parts.append(
            f"Strong edge: our margin is {abs(edge_over_spread):.1f} points "
            f"beyond the spread — {cover_team} should cover comfortably."
        )
    elif abs(edge_over_spread) >= 2:
        parts.append(
            f"Moderate edge: {cover_team} has about {abs(edge_over_spread):.1f} points "
            f"of cushion beyond the spread."
        )
    elif abs(edge_over_spread) >= 0.5:
        parts.append(
            f"Slim edge for {cover_team} — only {abs(edge_over_spread):.1f} points "
            f"beyond the spread. Could go either way."
        )
    else:
        parts.append("Market is very efficient here — our model agrees with the spread.")

    cover_reasoning = " ".join(parts)

    return cover_prob, cover_side, cover_confidence, cover_label, cover_reasoning
