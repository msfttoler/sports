"""Tests for app.models — Pydantic data models."""

import pytest
from datetime import UTC, datetime

from pydantic import ValidationError

from app.models import (
    ApiUsage,
    ArbLeg,
    ArbitrageOpportunity,
    BookmakerOdds,
    Event,
    OddsOutcome,
    RefreshResult,
)


class TestOddsOutcome:
    """Tests for OddsOutcome."""

    def test_create_with_required_fields(self):
        o = OddsOutcome(name="Chiefs", price=-150)
        assert o.name == "Chiefs"
        assert o.price == -150
        assert o.point is None

    def test_create_with_point(self):
        o = OddsOutcome(name="Over", price=-110, point=45.5)
        assert o.point == 45.5

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            OddsOutcome(price=-110)

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            OddsOutcome(name="Chiefs")


class TestBookmakerOdds:
    """Tests for BookmakerOdds."""

    def test_create_valid(self):
        bm = BookmakerOdds(
            bookmaker_key="fanduel",
            bookmaker_title="FanDuel",
            market="h2h",
            outcomes=[OddsOutcome(name="A", price=100)],
        )
        assert bm.bookmaker_key == "fanduel"
        assert len(bm.outcomes) == 1
        assert bm.last_update is None

    def test_with_last_update(self):
        bm = BookmakerOdds(
            bookmaker_key="dk",
            bookmaker_title="DraftKings",
            market="spreads",
            outcomes=[],
            last_update="2026-01-01T00:00:00Z",
        )
        assert bm.last_update == "2026-01-01T00:00:00Z"

    def test_empty_outcomes_allowed(self):
        bm = BookmakerOdds(
            bookmaker_key="x",
            bookmaker_title="X",
            market="h2h",
            outcomes=[],
        )
        assert bm.outcomes == []


class TestEvent:
    """Tests for Event."""

    def test_create_minimal(self):
        e = Event(
            id="e1",
            sport_key="nfl",
            sport_title="NFL",
            home_team="Home",
            away_team="Away",
            commence_time="2026-01-01T00:00:00Z",
        )
        assert e.id == "e1"
        assert e.bookmakers == []

    def test_create_with_bookmakers(self, bookmaker_fanduel):
        e = Event(
            id="e2",
            sport_key="nba",
            sport_title="NBA",
            home_team="H",
            away_team="A",
            commence_time="2026-01-01T00:00:00Z",
            bookmakers=[bookmaker_fanduel],
        )
        assert len(e.bookmakers) == 1

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            Event(
                sport_key="nfl",
                sport_title="NFL",
                home_team="H",
                away_team="A",
                commence_time="2026-01-01T00:00:00Z",
            )


class TestArbLeg:
    """Tests for ArbLeg."""

    def test_create_valid(self):
        leg = ArbLeg(
            outcome="Team A",
            bookmaker="FanDuel",
            price=150,
            implied_prob=0.4,
            stake_pct=46.81,
        )
        assert leg.outcome == "Team A"
        assert leg.price == 150

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            ArbLeg(outcome="Team A", bookmaker="FanDuel", price=150)


class TestArbitrageOpportunity:
    """Tests for ArbitrageOpportunity."""

    def test_create_with_defaults(self):
        opp = ArbitrageOpportunity(
            sport_key="nfl",
            event_id="e1",
            event_name="Away @ Home",
            home_team="Home",
            away_team="Away",
            commence_time="2026-01-01T00:00:00Z",
            market="h2h",
            profit_pct=2.5,
            total_implied_prob=0.975,
            legs=[],
        )
        assert opp.profit_pct == 2.5
        assert opp.detected_at is not None
        # detected_at should be a valid ISO string
        datetime.fromisoformat(opp.detected_at)

    def test_model_dump(self):
        opp = ArbitrageOpportunity(
            sport_key="nfl",
            event_id="e1",
            event_name="A @ H",
            home_team="H",
            away_team="A",
            commence_time="2026-01-01T00:00:00Z",
            market="h2h",
            profit_pct=1.0,
            total_implied_prob=0.99,
            legs=[
                ArbLeg(outcome="H", bookmaker="B1", price=150, implied_prob=0.4, stake_pct=40.0),
            ],
        )
        d = opp.model_dump()
        assert isinstance(d, dict)
        assert "legs" in d
        assert isinstance(d["legs"], list)


class TestRefreshResult:
    """Tests for RefreshResult."""

    def test_defaults(self):
        r = RefreshResult()
        assert r.events_fetched == 0
        assert r.arbitrage_found == 0
        assert r.sports_checked == []
        assert r.errors == []
        assert r.api_requests_remaining is None
        assert r.timestamp is not None

    def test_with_values(self):
        r = RefreshResult(events_fetched=10, arbitrage_found=2, errors=["err1"])
        assert r.events_fetched == 10
        assert r.errors == ["err1"]

    def test_model_dump(self):
        r = RefreshResult()
        d = r.model_dump()
        assert "events_fetched" in d
        assert "timestamp" in d


class TestApiUsage:
    """Tests for ApiUsage."""

    def test_defaults_none(self):
        u = ApiUsage()
        assert u.requests_used is None
        assert u.requests_remaining is None
        assert u.recorded_at is None

    def test_with_values(self):
        u = ApiUsage(requests_used=10, requests_remaining=490)
        assert u.requests_used == 10
        assert u.requests_remaining == 490
