"""
Arbitrage detection engine.

Scans odds across multiple bookmakers for the same event and identifies
situations where the combined implied probabilities sum to less than 100%,
guaranteeing a risk-free profit when staked correctly.
"""

import json
import logging

from app.models import Event, ArbitrageOpportunity, ArbLeg
from app.config import settings
from app.database import save_arbitrage

logger = logging.getLogger(__name__)


# ── Odds math helpers ─────────────────────────────────────────────────

def american_to_implied_prob(price: int) -> float:
    """
    Convert American odds to implied probability.
    
    +150 → 100 / (150 + 100) = 0.4000
    -130 → 130 / (130 + 100) = 0.5652
    """
    if price > 0:
        return 100.0 / (price + 100.0)
    else:
        return abs(price) / (abs(price) + 100.0)


def american_to_decimal(price: int) -> float:
    """Convert American odds to decimal odds."""
    if price > 0:
        return (price / 100.0) + 1.0
    else:
        return (100.0 / abs(price)) + 1.0


def calculate_arb_profit(implied_probs: list[float]) -> float:
    """
    Given implied probabilities for each outcome (best across books),
    return the arbitrage profit percentage.

    profit = (1 / sum_of_implied_probs - 1) * 100
    Positive value = guaranteed profit.
    """
    total = sum(implied_probs)
    if total <= 0:
        return -100.0
    return (1.0 / total - 1.0) * 100.0


def optimal_stakes(implied_probs: list[float], bankroll: float = 100.0) -> list[float]:
    """
    Calculate optimal stake distribution for an arbitrage bet.
    Each leg's stake is proportional to its implied probability
    relative to the sum.
    """
    total = sum(implied_probs)
    return [(p / total) * bankroll for p in implied_probs]


# ── Core detection ────────────────────────────────────────────────────

def detect_arbitrage(events: list[Event], min_profit_pct: float | None = None) -> list[ArbitrageOpportunity]:
    """
    Scan a list of events for arbitrage opportunities.

    For each event and each market, find the best price for every outcome
    across all bookmakers.  If the combined implied probability < 1.0,
    there is an arbitrage opportunity.
    """
    if min_profit_pct is None:
        min_profit_pct = settings.MIN_PROFIT_PCT

    opportunities: list[ArbitrageOpportunity] = []

    for event in events:
        # Group bookmaker odds by market
        markets: dict[str, dict[str, list[tuple[str, int]]]] = {}
        #  markets[market_key][outcome_name] = [(bookmaker_title, price), ...]

        for bm in event.bookmakers:
            mkt = bm.market
            if mkt not in markets:
                markets[mkt] = {}
            for outcome in bm.outcomes:
                if outcome.name not in markets[mkt]:
                    markets[mkt][outcome.name] = []
                markets[mkt][outcome.name].append((bm.bookmaker_title, outcome.price))

        # For each market, find best odds per outcome
        for market_key, outcome_map in markets.items():
            outcome_names = list(outcome_map.keys())
            if len(outcome_names) < 2:
                continue

            # Find the best (highest decimal / lowest implied prob) price for each outcome
            best_per_outcome: list[tuple[str, str, int, float]] = []  # (outcome, book, price, impl_prob)
            for name in outcome_names:
                lines = outcome_map[name]
                # Best = highest American odds → highest decimal → lowest implied prob
                best_book, best_price = max(lines, key=lambda x: american_to_decimal(x[1]))
                impl_prob = american_to_implied_prob(best_price)
                best_per_outcome.append((name, best_book, best_price, impl_prob))

            implied_probs = [x[3] for x in best_per_outcome]
            total_implied = sum(implied_probs)
            profit = calculate_arb_profit(implied_probs)

            if profit >= min_profit_pct:
                stakes = optimal_stakes(implied_probs)
                legs = [
                    ArbLeg(
                        outcome=name,
                        bookmaker=book,
                        price=price,
                        implied_prob=round(prob, 6),
                        stake_pct=round(stake, 2),
                    )
                    for (name, book, price, prob), stake in zip(best_per_outcome, stakes, strict=True)
                ]

                opp = ArbitrageOpportunity(
                    sport_key=event.sport_key,
                    event_id=event.id,
                    event_name=f"{event.away_team} @ {event.home_team}",
                    home_team=event.home_team,
                    away_team=event.away_team,
                    commence_time=event.commence_time,
                    market=market_key,
                    profit_pct=round(profit, 4),
                    total_implied_prob=round(total_implied, 6),
                    legs=legs,
                )
                opportunities.append(opp)
                logger.info(
                    "ARB FOUND: %s (%s) – %.2f%% profit across %s",
                    opp.event_name,
                    market_key,
                    profit,
                    [leg.bookmaker for leg in legs],
                )

    # Persist to database
    if opportunities:
        db_rows = [
            {
                "sport_key": o.sport_key,
                "event_id": o.event_id,
                "event_name": o.event_name,
                "home_team": o.home_team,
                "away_team": o.away_team,
                "commence_time": o.commence_time,
                "market": o.market,
                "profit_pct": o.profit_pct,
                "legs": json.dumps([leg.model_dump() for leg in o.legs]),
                "total_implied_prob": o.total_implied_prob,
                "detected_at": o.detected_at,
            }
            for o in opportunities
        ]
        save_arbitrage(db_rows)

    logger.info("Scanned %d events – found %d arb opportunities", len(events), len(opportunities))
    return opportunities
