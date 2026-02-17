"""
Value Bet Detector — finds edges where our model disagrees with the books.

Compares our ML win probabilities to bookmaker implied odds.
When our model says a team has a higher chance of winning than the
books imply, that's a potential value bet.

Includes Kelly Criterion for optimal stake sizing.
"""

import logging
import math

from app.arbitrage import american_to_implied_prob, american_to_decimal
from app.models import Event, GamePrediction, ValueBet

logger = logging.getLogger(__name__)

MIN_EDGE_PCT = 0.03  # 3% minimum edge to surface a value bet


def kelly_criterion(our_prob: float, decimal_odds: float) -> float:
    """
    Calculate Kelly Criterion fraction.

    kelly = (p * (d - 1) - (1 - p)) / (d - 1)

    Where p = our probability, d = decimal odds.
    Negative = no bet. We cap at 25% (quarter Kelly for safety).
    """
    if decimal_odds <= 1.0 or our_prob <= 0 or our_prob >= 1:
        return 0.0
    q = 1.0 - our_prob
    numerator = our_prob * (decimal_odds - 1) - q
    denominator = decimal_odds - 1
    if denominator <= 0:
        return 0.0
    kelly = numerator / denominator
    # Quarter Kelly for risk management
    return max(0.0, min(kelly * 0.25, 0.25))


def find_value_bets(
    predictions: list[GamePrediction],
    events: list[Event],
    min_edge: float = MIN_EDGE_PCT,
    min_confidence: float = 0.55,
) -> list[ValueBet]:
    """
    Cross-reference our predictions with bookmaker odds to find value bets.

    A value bet exists when:
      our_prob > book_implied_prob + min_edge
    """
    # Index events by ID for quick lookup
    event_map: dict[str, Event] = {e.id: e for e in events}

    value_bets: list[ValueBet] = []

    for pred in predictions:
        if pred.confidence < min_confidence:
            continue

        event = event_map.get(pred.event_id)
        if not event or not event.bookmakers:
            continue

        # Check both sides (home and away)
        for team, our_prob in [
            (pred.home_team, pred.home_win_prob),
            (pred.away_team, pred.away_win_prob),
        ]:
            # Find the best price across all bookmakers for this team
            best_price: int | None = None
            best_book: str = ""

            for bm in event.bookmakers:
                if bm.market != "h2h":
                    continue
                for outcome in bm.outcomes:
                    if outcome.name == team:
                        if best_price is None or american_to_decimal(outcome.price) > american_to_decimal(best_price):
                            best_price = outcome.price
                            best_book = bm.bookmaker_title

            if best_price is None:
                continue

            book_implied = american_to_implied_prob(best_price)
            edge = our_prob - book_implied

            if edge >= min_edge:
                decimal_odds = american_to_decimal(best_price)
                kelly = kelly_criterion(our_prob, decimal_odds)

                vb = ValueBet(
                    event_id=pred.event_id,
                    sport_key=pred.sport_key,
                    event_name=f"{pred.away_team} @ {pred.home_team}",
                    commence_time=pred.commence_time,
                    team=team,
                    our_prob=round(our_prob, 4),
                    book_implied_prob=round(book_implied, 4),
                    best_price=best_price,
                    best_bookmaker=best_book,
                    edge_pct=round(edge, 4),
                    confidence=pred.confidence,
                    confidence_label=pred.confidence_label,
                    kelly_fraction=round(kelly, 4),
                )
                value_bets.append(vb)

                logger.info(
                    "VALUE BET: %s (%s) — our %.0f%% vs book %.0f%% = %.1f%% edge @ %s (%s)",
                    team,
                    pred.sport_key,
                    our_prob * 100,
                    book_implied * 100,
                    edge * 100,
                    best_book,
                    best_price,
                )

    # Sort by edge descending
    value_bets.sort(key=lambda v: v.edge_pct, reverse=True)

    logger.info(
        "Found %d value bets from %d predictions (min edge=%.0f%%, min conf=%.0f%%)",
        len(value_bets),
        len(predictions),
        min_edge * 100,
        min_confidence * 100,
    )
    return value_bets
