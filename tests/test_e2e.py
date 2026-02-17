"""
Playwright End-to-End Tests for the Sports AI Dashboard.

Tests the full user experience: page load, tab navigation, prediction cards,
clickable detail expand, sport switching, bet tracker flow, and more.

Run with:
    pytest tests/test_e2e.py --headed   # watch the browser
    pytest tests/test_e2e.py            # headless
"""

import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="session")
def browser_context_args():
    return {"base_url": BASE_URL}


# ── Page Load ─────────────────────────────────────────────────────────

class TestPageLoad:
    """Dashboard loads correctly."""

    def test_page_loads(self, page: Page):
        page.goto("/")
        expect(page).to_have_title(re.compile("Sports AI"))

    def test_header_visible(self, page: Page):
        page.goto("/")
        expect(page.locator("h1")).to_contain_text("Sports")

    def test_tabs_visible(self, page: Page):
        page.goto("/")
        expect(page.get_by_text("Predictions")).to_be_visible()
        expect(page.get_by_text("Standings")).to_be_visible()
        expect(page.get_by_text("Value Bets")).to_be_visible()
        expect(page.get_by_text("Arbitrage")).to_be_visible()
        expect(page.get_by_text("Tracker")).to_be_visible()

    def test_sport_selector_visible(self, page: Page):
        page.goto("/")
        sel = page.locator("#sportSel")
        expect(sel).to_be_visible()
        # Should have multiple sports
        options = sel.locator("option").all()
        assert len(options) >= 4


# ── Tab Navigation ────────────────────────────────────────────────────

class TestTabNavigation:
    """Tabs switch panels correctly."""

    def test_predictions_tab_default(self, page: Page):
        page.goto("/")
        expect(page.locator("#predictions")).to_be_visible()

    def test_switch_to_standings(self, page: Page):
        page.goto("/")
        page.get_by_text("Standings").click()
        expect(page.locator("#standings")).to_be_visible()
        expect(page.locator("#predictions")).to_be_hidden()

    def test_switch_to_tracker(self, page: Page):
        page.goto("/")
        page.get_by_text("Tracker").click()
        expect(page.locator("#tracker")).to_be_visible()

    def test_switch_to_arbitrage(self, page: Page):
        page.goto("/")
        page.get_by_text("Arbitrage").click()
        expect(page.locator("#arbitrage")).to_be_visible()

    def test_switch_back_to_predictions(self, page: Page):
        page.goto("/")
        page.get_by_text("Standings").click()
        page.get_by_text("Predictions").click()
        expect(page.locator("#predictions")).to_be_visible()


# ── Predictions ───────────────────────────────────────────────────────

class TestPredictions:
    """Prediction cards load and are interactive."""

    def test_predictions_load(self, page: Page):
        page.goto("/")
        # Wait for predictions to load (cards OR empty state)
        page.wait_for_selector("[data-testid='pred-card'], .empty", timeout=15000)

    def test_stat_cards_show(self, page: Page):
        page.goto("/")
        page.wait_for_selector("#predStats .card", timeout=15000)
        cards = page.locator("#predStats .card").all()
        assert len(cards) >= 3  # Predictions, Value Bets, Teams at minimum

    def test_prediction_card_expandable(self, page: Page):
        page.goto("/")
        pred = page.locator("[data-testid='pred-card']").first
        if pred.count() > 0:
            # Click to expand
            pred.click()
            # Should show feature breakdown
            expect(pred.locator(".pred-details")).to_be_visible()
            # Click again to collapse
            pred.click()
            expect(pred.locator(".pred-details")).to_be_hidden()

    def test_prediction_has_winner(self, page: Page):
        page.goto("/")
        pred = page.locator("[data-testid='pred-card']").first
        if pred.count() > 0:
            expect(pred.locator(".pred-winner")).to_be_visible()
            expect(pred.locator(".pred-conf")).to_be_visible()

    def test_track_moneyline_button(self, page: Page):
        page.goto("/")
        page.wait_for_selector("[data-testid='pred-card']", timeout=15000)
        btn = page.get_by_text("Track Moneyline").first
        if btn.count() > 0:
            btn.click()
            expect(page.locator("#betModal")).to_have_class(re.compile("open"))
            # Modal should be pre-filled
            expect(page.locator("#bEvent")).not_to_have_value("")
            expect(page.locator("#bPick")).not_to_have_value("")
            # Close it
            page.get_by_text("Cancel").click()


# ── Standings ─────────────────────────────────────────────────────────

class TestStandings:
    """Standings table loads with data."""

    def test_standings_load(self, page: Page):
        page.goto("/")
        page.get_by_text("Standings").click()
        page.wait_for_selector("#standingsTable table, #standingsTable .empty", timeout=15000)

    def test_standings_has_rows(self, page: Page):
        page.goto("/")
        page.get_by_text("Standings").click()
        page.wait_for_selector("#standingsTable table", timeout=15000)
        rows = page.locator("#standingsTable tbody tr").all()
        assert len(rows) > 0


# ── Sport Switching ───────────────────────────────────────────────────

class TestSportSwitching:
    """Switching sports reloads data."""

    def test_switch_to_nfl(self, page: Page):
        page.goto("/")
        page.select_option("#sportSel", "NFL")
        # Should trigger a reload — wait for it
        page.wait_for_timeout(2000)
        # Badge should show sport or at least page shouldn't crash
        expect(page.locator("#predStats")).to_be_visible()


# ── Bet Tracker ───────────────────────────────────────────────────────

class TestBetTracker:
    """Bet tracker modal and list work."""

    def test_tracker_tab_loads(self, page: Page):
        page.goto("/")
        page.get_by_text("Tracker").click()
        expect(page.locator("#tracker")).to_be_visible()

    def test_log_bet_opens_modal(self, page: Page):
        page.goto("/")
        page.get_by_text("Tracker").click()
        page.get_by_text("+ Log Bet").click()
        expect(page.locator("#betModal")).to_have_class(re.compile("open"))

    def test_log_bet_and_save(self, page: Page):
        page.goto("/")
        page.get_by_text("Tracker").click()
        page.get_by_text("+ Log Bet").click()

        page.fill("#bEvent", "Test Team A vs Test Team B")
        page.fill("#bPick", "Test Team A")
        page.fill("#bOdds", "-110")
        page.fill("#bStake", "100")
        page.click("button:has-text('Save Bet')")

        # Modal should close
        page.wait_for_timeout(500)
        expect(page.locator("#betModal")).not_to_have_class(re.compile("open"))

    def test_check_scores_button(self, page: Page):
        page.goto("/")
        page.get_by_text("Tracker").click()
        btn = page.get_by_text("Check Scores")
        expect(btn).to_be_visible()


# ── API Endpoints ─────────────────────────────────────────────────────

class TestAPIEndpoints:
    """Backend API endpoints return valid JSON."""

    def test_api_status(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/status")
        assert resp.ok
        data = resp.json()
        assert "sports_tracked" in data

    def test_api_predictions(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/predictions?sport=NBA")
        assert resp.ok
        data = resp.json()
        assert "predictions" in data
        assert "prediction_count" in data

    def test_api_standings(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/standings?sport=NBA")
        assert resp.ok
        data = resp.json()
        assert "standings" in data

    def test_api_injuries(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/injuries?sport=NBA")
        assert resp.ok
        data = resp.json()
        assert "injuries" in data

    def test_api_arbitrage(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/arbitrage")
        assert resp.ok
        data = resp.json()
        assert "arbitrage" in data

    def test_api_bets(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/bets")
        assert resp.ok
        data = resp.json()
        assert "bets" in data
        assert "summary" in data

    def test_api_sports(self, page: Page):
        resp = page.request.get(f"{BASE_URL}/api/sports")
        assert resp.ok
        data = resp.json()
        assert "sports" in data
        assert "NBA" in data["sports"]
