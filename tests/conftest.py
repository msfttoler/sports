"""Shared fixtures for the Sports Arbitrage Finder test suite."""

import pytest

from app.models import (
    ArbLeg,
    ArbitrageOpportunity,
    BookmakerOdds,
    Event,
    OddsOutcome,
    RefreshResult,
)


# ── Sample Odds Outcomes ──────────────────────────────────────────────

@pytest.fixture
def outcome_teamA_plus150():
    return OddsOutcome(name="Team A", price=150)


@pytest.fixture
def outcome_teamB_minus130():
    return OddsOutcome(name="Team B", price=-130)


# ── Sample Bookmaker Odds ─────────────────────────────────────────────

@pytest.fixture
def bookmaker_fanduel(outcome_teamA_plus150, outcome_teamB_minus130):
    return BookmakerOdds(
        bookmaker_key="fanduel",
        bookmaker_title="FanDuel",
        market="h2h",
        outcomes=[outcome_teamA_plus150, outcome_teamB_minus130],
        last_update="2026-02-16T12:00:00Z",
    )


@pytest.fixture
def bookmaker_draftkings():
    return BookmakerOdds(
        bookmaker_key="draftkings",
        bookmaker_title="DraftKings",
        market="h2h",
        outcomes=[
            OddsOutcome(name="Team A", price=160),
            OddsOutcome(name="Team B", price=-120),
        ],
    )


@pytest.fixture
def bookmaker_arb_teamA():
    """Bookmaker offering generous Team A line (for arb scenarios)."""
    return BookmakerOdds(
        bookmaker_key="book_a",
        bookmaker_title="Book A",
        market="h2h",
        outcomes=[
            OddsOutcome(name="Team A", price=150),
            OddsOutcome(name="Team B", price=-200),
        ],
    )


@pytest.fixture
def bookmaker_arb_teamB():
    """Bookmaker offering generous Team B line (for arb scenarios)."""
    return BookmakerOdds(
        bookmaker_key="book_b",
        bookmaker_title="Book B",
        market="h2h",
        outcomes=[
            OddsOutcome(name="Team A", price=-300),
            OddsOutcome(name="Team B", price=120),
        ],
    )


# ── Sample Events ─────────────────────────────────────────────────────

@pytest.fixture
def sample_event(bookmaker_fanduel, bookmaker_draftkings):
    return Event(
        id="evt_001",
        sport_key="americanfootball_nfl",
        sport_title="NFL",
        home_team="Team A",
        away_team="Team B",
        commence_time="2026-02-16T18:00:00Z",
        bookmakers=[bookmaker_fanduel, bookmaker_draftkings],
    )


@pytest.fixture
def arb_event(bookmaker_arb_teamA, bookmaker_arb_teamB):
    """Event with an arbitrage opportunity (combined implied < 100%)."""
    return Event(
        id="evt_arb",
        sport_key="basketball_nba",
        sport_title="NBA",
        home_team="Team A",
        away_team="Team B",
        commence_time="2026-02-16T20:00:00Z",
        bookmakers=[bookmaker_arb_teamA, bookmaker_arb_teamB],
    )


@pytest.fixture
def event_no_bookmakers():
    return Event(
        id="evt_empty",
        sport_key="americanfootball_nfl",
        sport_title="NFL",
        home_team="Home",
        away_team="Away",
        commence_time="2026-02-16T18:00:00Z",
        bookmakers=[],
    )


@pytest.fixture
def event_single_outcome():
    """Event where a market has only one outcome (can't arb)."""
    return Event(
        id="evt_single",
        sport_key="americanfootball_nfl",
        sport_title="NFL",
        home_team="Home",
        away_team="Away",
        commence_time="2026-02-16T18:00:00Z",
        bookmakers=[
            BookmakerOdds(
                bookmaker_key="book1",
                bookmaker_title="Book1",
                market="h2h",
                outcomes=[OddsOutcome(name="Team A", price=-110)],
            )
        ],
    )


# ── Sample API response data ─────────────────────────────────────────

@pytest.fixture
def odds_api_response():
    """Raw JSON structure matching The Odds API response."""
    return [
        {
            "id": "abc123",
            "sport_key": "americanfootball_nfl",
            "sport_title": "NFL",
            "home_team": "Chiefs",
            "away_team": "Bills",
            "commence_time": "2026-02-16T18:00:00Z",
            "bookmakers": [
                {
                    "key": "fanduel",
                    "title": "FanDuel",
                    "last_update": "2026-02-16T12:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Chiefs", "price": -150},
                                {"name": "Bills", "price": 130},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
