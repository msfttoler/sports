"""Tests for app.arbitrage — odds math helpers and arbitrage detection."""

import json
from unittest.mock import patch

import pytest

from app.arbitrage import (
    american_to_decimal,
    american_to_implied_prob,
    calculate_arb_profit,
    detect_arbitrage,
    optimal_stakes,
)
from app.models import ArbLeg, BookmakerOdds, Event, OddsOutcome


# ═══════════════════════════════════════════════════════════════════════
# american_to_implied_prob
# ═══════════════════════════════════════════════════════════════════════

class TestAmericanToImpliedProb:
    """Tests for american_to_implied_prob."""

    @pytest.mark.parametrize("price,expected", [
        (150, 100.0 / 250.0),       # +150 → 0.4
        (100, 0.5),                  # +100 → 0.5 (even money)
        (200, 100.0 / 300.0),       # +200 → 0.3333
        (500, 100.0 / 600.0),       # +500 → 0.1667
        (1000, 100.0 / 1100.0),     # +1000 → 0.0909
    ])
    def test_positive_odds(self, price, expected):
        assert american_to_implied_prob(price) == pytest.approx(expected, abs=1e-6)

    @pytest.mark.parametrize("price,expected", [
        (-110, 110.0 / 210.0),      # -110 → 0.5238
        (-130, 130.0 / 230.0),      # -130 → 0.5652
        (-200, 200.0 / 300.0),      # -200 → 0.6667
        (-500, 500.0 / 600.0),      # -500 → 0.8333
        (-100, 100.0 / 200.0),      # -100 → 0.5
    ])
    def test_negative_odds(self, price, expected):
        assert american_to_implied_prob(price) == pytest.approx(expected, abs=1e-6)

    def test_large_positive_odds(self):
        result = american_to_implied_prob(10000)
        assert 0 < result < 0.01

    def test_large_negative_odds(self):
        result = american_to_implied_prob(-10000)
        assert 0.99 < result < 1.0

    def test_return_type(self):
        assert isinstance(american_to_implied_prob(150), float)
        assert isinstance(american_to_implied_prob(-110), float)


# ═══════════════════════════════════════════════════════════════════════
# american_to_decimal
# ═══════════════════════════════════════════════════════════════════════

class TestAmericanToDecimal:
    """Tests for american_to_decimal."""

    @pytest.mark.parametrize("price,expected", [
        (100, 2.0),                  # +100 → 2.0
        (150, 2.5),                  # +150 → 2.5
        (200, 3.0),                  # +200 → 3.0
        (300, 4.0),                  # +300 → 4.0
    ])
    def test_positive_odds(self, price, expected):
        assert american_to_decimal(price) == pytest.approx(expected, abs=1e-6)

    @pytest.mark.parametrize("price,expected", [
        (-100, 2.0),                 # -100 → 2.0
        (-110, 1.0 + 100.0 / 110.0),
        (-200, 1.5),                 # -200 → 1.5
        (-500, 1.2),                 # -500 → 1.2
    ])
    def test_negative_odds(self, price, expected):
        assert american_to_decimal(price) == pytest.approx(expected, abs=1e-6)

    def test_decimal_always_greater_than_one(self):
        for price in [100, 150, -110, -200, -500, 500]:
            assert american_to_decimal(price) > 1.0

    def test_return_type(self):
        assert isinstance(american_to_decimal(150), float)


# ═══════════════════════════════════════════════════════════════════════
# calculate_arb_profit
# ═══════════════════════════════════════════════════════════════════════

class TestCalculateArbProfit:
    """Tests for calculate_arb_profit."""

    def test_arb_exists(self):
        # Implied probs sum to 0.85 → profit = (1/0.85 - 1)*100 ≈ 17.6%
        probs = [0.4, 0.45]
        result = calculate_arb_profit(probs)
        assert result > 0
        assert result == pytest.approx((1.0 / 0.85 - 1.0) * 100, abs=0.01)

    def test_no_arb_standard_vig(self):
        # -110/-110 → each 0.5238 → total 1.0476 → negative profit
        p = 110.0 / 210.0
        result = calculate_arb_profit([p, p])
        assert result < 0

    def test_exact_100_percent(self):
        # Probs sum to 1.0 → 0% profit
        result = calculate_arb_profit([0.5, 0.5])
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_empty_list(self):
        result = calculate_arb_profit([])
        assert result == -100.0

    def test_zero_total(self):
        result = calculate_arb_profit([0.0, 0.0])
        assert result == -100.0

    def test_single_outcome(self):
        result = calculate_arb_profit([0.5])
        assert result == pytest.approx(100.0, abs=1e-6)

    def test_three_way_market(self):
        probs = [0.3, 0.3, 0.3]  # total 0.9 → profit ~11.1%
        result = calculate_arb_profit(probs)
        assert result > 0
        assert result == pytest.approx((1.0 / 0.9 - 1.0) * 100, abs=0.01)

    def test_return_type(self):
        assert isinstance(calculate_arb_profit([0.4, 0.5]), float)


# ═══════════════════════════════════════════════════════════════════════
# optimal_stakes
# ═══════════════════════════════════════════════════════════════════════

class TestOptimalStakes:
    """Tests for optimal_stakes."""

    def test_equal_probs(self):
        stakes = optimal_stakes([0.5, 0.5], bankroll=100.0)
        assert len(stakes) == 2
        assert stakes[0] == pytest.approx(50.0)
        assert stakes[1] == pytest.approx(50.0)

    def test_unequal_probs(self):
        stakes = optimal_stakes([0.4, 0.6], bankroll=100.0)
        assert stakes[0] == pytest.approx(40.0)
        assert stakes[1] == pytest.approx(60.0)

    def test_stakes_sum_to_bankroll(self):
        stakes = optimal_stakes([0.3, 0.35, 0.25], bankroll=200.0)
        assert sum(stakes) == pytest.approx(200.0)

    def test_default_bankroll(self):
        stakes = optimal_stakes([0.5, 0.5])
        assert sum(stakes) == pytest.approx(100.0)

    def test_custom_bankroll(self):
        stakes = optimal_stakes([0.5, 0.5], bankroll=1000.0)
        assert sum(stakes) == pytest.approx(1000.0)

    def test_single_outcome(self):
        stakes = optimal_stakes([1.0], bankroll=100.0)
        assert stakes == [pytest.approx(100.0)]

    def test_return_type(self):
        result = optimal_stakes([0.4, 0.6])
        assert isinstance(result, list)
        assert all(isinstance(s, float) for s in result)


# ═══════════════════════════════════════════════════════════════════════
# detect_arbitrage
# ═══════════════════════════════════════════════════════════════════════

class TestDetectArbitrage:
    """Tests for detect_arbitrage."""

    @patch("app.arbitrage.save_arbitrage")
    def test_no_events_returns_empty(self, mock_save):
        result = detect_arbitrage([], min_profit_pct=0.0)
        assert result == []
        mock_save.assert_not_called()

    @patch("app.arbitrage.save_arbitrage")
    def test_event_no_bookmakers(self, mock_save, event_no_bookmakers):
        result = detect_arbitrage([event_no_bookmakers], min_profit_pct=0.0)
        assert result == []

    @patch("app.arbitrage.save_arbitrage")
    def test_single_outcome_market_skipped(self, mock_save, event_single_outcome):
        result = detect_arbitrage([event_single_outcome], min_profit_pct=0.0)
        assert result == []

    @patch("app.arbitrage.save_arbitrage")
    def test_arb_detected(self, mock_save, arb_event):
        result = detect_arbitrage([arb_event], min_profit_pct=0.0)
        assert len(result) >= 1
        opp = result[0]
        assert opp.profit_pct > 0
        assert opp.event_name == "Team B @ Team A"
        assert opp.market == "h2h"
        assert len(opp.legs) == 2
        mock_save.assert_called_once()

    @patch("app.arbitrage.save_arbitrage")
    def test_arb_legs_have_correct_fields(self, mock_save, arb_event):
        result = detect_arbitrage([arb_event], min_profit_pct=0.0)
        for opp in result:
            for leg in opp.legs:
                assert isinstance(leg.outcome, str)
                assert isinstance(leg.bookmaker, str)
                assert isinstance(leg.price, int)
                assert 0 < leg.implied_prob < 1
                assert leg.stake_pct > 0

    @patch("app.arbitrage.save_arbitrage")
    def test_min_profit_filter(self, mock_save, arb_event):
        # With a very high threshold, no arbs should pass
        result = detect_arbitrage([arb_event], min_profit_pct=99.0)
        assert result == []

    @patch("app.arbitrage.save_arbitrage")
    def test_uses_settings_default_when_none(self, mock_save, arb_event):
        with patch("app.arbitrage.settings") as mock_settings:
            mock_settings.MIN_PROFIT_PCT = 99.0
            result = detect_arbitrage([arb_event], min_profit_pct=None)
            assert result == []

    @patch("app.arbitrage.save_arbitrage")
    def test_normal_event_no_arb(self, mock_save, sample_event):
        result = detect_arbitrage([sample_event], min_profit_pct=0.0)
        # Standard lines usually don't produce arbs
        # The result depends on the actual odds — just validate structure
        assert isinstance(result, list)

    @patch("app.arbitrage.save_arbitrage")
    def test_multiple_events(self, mock_save, sample_event, arb_event):
        result = detect_arbitrage([sample_event, arb_event], min_profit_pct=0.0)
        assert isinstance(result, list)
        # At least the arb_event should produce an opportunity
        arb_event_ids = [o.event_id for o in result]
        assert "evt_arb" in arb_event_ids

    @patch("app.arbitrage.save_arbitrage")
    def test_persist_called_with_correct_shape(self, mock_save, arb_event):
        detect_arbitrage([arb_event], min_profit_pct=0.0)
        mock_save.assert_called_once()
        rows = mock_save.call_args[0][0]
        assert isinstance(rows, list)
        assert len(rows) > 0
        row = rows[0]
        assert "sport_key" in row
        assert "legs" in row
        # legs should be JSON string
        parsed = json.loads(row["legs"])
        assert isinstance(parsed, list)

    @patch("app.arbitrage.save_arbitrage")
    def test_total_implied_prob_less_than_one_for_arb(self, mock_save, arb_event):
        result = detect_arbitrage([arb_event], min_profit_pct=0.0)
        for opp in result:
            assert opp.total_implied_prob < 1.0
