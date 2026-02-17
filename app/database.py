"""
SQLite database layer for persisting odds snapshots and arbitrage opportunities.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


def _ensure_dir():
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS odds_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport_key TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                market TEXT NOT NULL,
                outcome_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                point REAL,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(event_id, bookmaker, market, outcome_name, fetched_at)
            );

            CREATE INDEX IF NOT EXISTS idx_odds_event ON odds_snapshots(event_id);
            CREATE INDEX IF NOT EXISTS idx_odds_sport ON odds_snapshots(sport_key);
            CREATE INDEX IF NOT EXISTS idx_odds_fetched ON odds_snapshots(fetched_at);

            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport_key TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                market TEXT NOT NULL,
                profit_pct REAL NOT NULL,
                legs TEXT NOT NULL,          -- JSON array of {outcome, bookmaker, price, stake_pct}
                total_implied_prob REAL NOT NULL,
                detected_at TEXT NOT NULL DEFAULT (datetime('now')),
                still_live INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_arb_profit ON arbitrage_opportunities(profit_pct DESC);
            CREATE INDEX IF NOT EXISTS idx_arb_detected ON arbitrage_opportunities(detected_at);
            CREATE INDEX IF NOT EXISTS idx_arb_live ON arbitrage_opportunities(still_live);

            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requests_used INTEGER,
                requests_remaining INTEGER,
                recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bet_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT NOT NULL,
                event_name TEXT NOT NULL,
                home_team TEXT,
                away_team TEXT,
                bet_type TEXT NOT NULL,         -- 'moneyline', 'spread', 'total', 'other'
                pick TEXT NOT NULL,             -- who/what you bet on
                spread_line REAL,              -- spread line if bet_type='spread' (e.g. -3.5)
                total_line REAL,               -- total line if bet_type='total' (e.g. 220.5)
                odds INTEGER NOT NULL,          -- American odds received
                stake REAL NOT NULL,            -- amount wagered
                potential_win REAL NOT NULL,     -- potential profit (not including stake)
                our_confidence REAL,            -- model confidence at time of bet (0-1)
                result TEXT DEFAULT 'pending',  -- 'win', 'loss', 'push', 'pending'
                actual_pnl REAL DEFAULT 0,      -- actual profit/loss after result
                home_score INTEGER,             -- final home score (filled by auto-settle)
                away_score INTEGER,             -- final away score (filled by auto-settle)
                notes TEXT,
                placed_at TEXT NOT NULL DEFAULT (datetime('now')),
                settled_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_bet_result ON bet_tracker(result);
            CREATE INDEX IF NOT EXISTS idx_bet_placed ON bet_tracker(placed_at);
            CREATE INDEX IF NOT EXISTS idx_bet_sport ON bet_tracker(sport);
        """)


def save_odds(rows: list[dict]):
    """Bulk-insert odds snapshot rows."""
    if not rows:
        return
    with get_db() as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO odds_snapshots
            (sport_key, event_id, event_name, home_team, away_team, commence_time,
             bookmaker, market, outcome_name, price, point, fetched_at)
            VALUES (:sport_key, :event_id, :event_name, :home_team, :away_team,
                    :commence_time, :bookmaker, :market, :outcome_name, :price,
                    :point, :fetched_at)
        """, rows)


def save_arbitrage(opps: list[dict]):
    """Save detected arbitrage opportunities."""
    if not opps:
        return
    with get_db() as conn:
        # Mark all previous as stale
        conn.execute("UPDATE arbitrage_opportunities SET still_live = 0")
        conn.executemany("""
            INSERT INTO arbitrage_opportunities
            (sport_key, event_id, event_name, home_team, away_team, commence_time,
             market, profit_pct, legs, total_implied_prob, detected_at, still_live)
            VALUES (:sport_key, :event_id, :event_name, :home_team, :away_team,
                    :commence_time, :market, :profit_pct, :legs,
                    :total_implied_prob, :detected_at, 1)
        """, opps)


def get_live_arbitrage() -> list[dict]:
    """Return currently-live arbitrage opportunities."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM arbitrage_opportunities
            WHERE still_live = 1
            ORDER BY profit_pct DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_arbitrage_history(limit: int = 100) -> list[dict]:
    """Return recent historical arbitrage opportunities."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM arbitrage_opportunities
            ORDER BY detected_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_latest_odds(sport_key: str | None = None) -> list[dict]:
    """Get the latest odds snapshot."""
    with get_db() as conn:
        if sport_key:
            rows = conn.execute("""
                SELECT * FROM odds_snapshots
                WHERE fetched_at = (SELECT MAX(fetched_at) FROM odds_snapshots WHERE sport_key = ?)
                AND sport_key = ?
                ORDER BY commence_time, event_name, bookmaker
            """, (sport_key, sport_key)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM odds_snapshots
                WHERE fetched_at = (SELECT MAX(fetched_at) FROM odds_snapshots)
                ORDER BY commence_time, event_name, bookmaker
            """).fetchall()
        return [dict(r) for r in rows]


def save_api_usage(used: int, remaining: int):
    """Record API usage stats."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO api_usage (requests_used, requests_remaining)
            VALUES (?, ?)
        """, (used, remaining))


def get_api_usage() -> dict | None:
    """Get latest API usage stats."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM api_usage ORDER BY recorded_at DESC LIMIT 1
        """).fetchone()
        return dict(row) if row else None


# ── Bet Tracker ───────────────────────────────────────────────────────

def add_bet(bet: dict) -> int:
    """Add a new bet to the tracker. Returns the bet ID."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO bet_tracker
            (sport, event_name, home_team, away_team, bet_type, pick,
             spread_line, total_line, odds, stake, potential_win,
             our_confidence, result, notes)
            VALUES (:sport, :event_name, :home_team, :away_team, :bet_type, :pick,
                    :spread_line, :total_line, :odds, :stake,
                    :potential_win, :our_confidence, 'pending', :notes)
        """, bet)
        return cursor.lastrowid


def settle_bet(bet_id: int, result: str) -> dict | None:
    """Settle a pending bet as 'win', 'loss', or 'push'."""
    with get_db() as conn:
        # Get the bet first
        row = conn.execute("SELECT * FROM bet_tracker WHERE id = ?", (bet_id,)).fetchone()
        if not row:
            return None
        bet = dict(row)

        if result == "win":
            pnl = bet["potential_win"]
        elif result == "loss":
            pnl = -bet["stake"]
        else:  # push
            pnl = 0.0

        conn.execute("""
            UPDATE bet_tracker
            SET result = ?, actual_pnl = ?, settled_at = datetime('now')
            WHERE id = ?
        """, (result, pnl, bet_id))

        bet["result"] = result
        bet["actual_pnl"] = pnl
        return bet


def get_all_bets(limit: int = 200) -> list[dict]:
    """Get all tracked bets, newest first."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM bet_tracker ORDER BY placed_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_bet_summary() -> dict:
    """Get aggregate stats for the bet tracker."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM bet_tracker").fetchone()[0]
        settled = conn.execute(
            "SELECT COUNT(*) FROM bet_tracker WHERE result != 'pending'"
        ).fetchone()[0]
        wins = conn.execute(
            "SELECT COUNT(*) FROM bet_tracker WHERE result = 'win'"
        ).fetchone()[0]
        losses = conn.execute(
            "SELECT COUNT(*) FROM bet_tracker WHERE result = 'loss'"
        ).fetchone()[0]
        pushes = conn.execute(
            "SELECT COUNT(*) FROM bet_tracker WHERE result = 'push'"
        ).fetchone()[0]
        pending = total - settled
        total_staked = conn.execute(
            "SELECT COALESCE(SUM(stake), 0) FROM bet_tracker WHERE result != 'pending'"
        ).fetchone()[0]
        total_pnl = conn.execute(
            "SELECT COALESCE(SUM(actual_pnl), 0) FROM bet_tracker WHERE result != 'pending'"
        ).fetchone()[0]
        roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0

        return {
            "total_bets": total,
            "settled": settled,
            "pending": pending,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "win_rate": round(wins / settled * 100, 1) if settled > 0 else 0.0,
            "total_staked": round(total_staked, 2),
            "total_pnl": round(total_pnl, 2),
            "roi": round(roi, 1),
        }


def get_pending_bets() -> list[dict]:
    """Get all bets with result='pending'."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM bet_tracker WHERE result = 'pending'
            ORDER BY placed_at ASC
        """).fetchall()
        return [dict(r) for r in rows]


def auto_settle_with_score(bet_id: int, home_score: int, away_score: int) -> dict | None:
    """
    Auto-settle a bet using final game scores.

    Determines win/loss/push based on bet_type:
    - moneyline: did the picked team win?
    - spread: did picked team cover the spread_line?
    - total: did total score go over/under the total_line?
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bet_tracker WHERE id = ?", (bet_id,)).fetchone()
        if not row:
            return None
        bet = dict(row)

        if bet["result"] != "pending":
            return bet  # already settled

        pick = bet["pick"]
        bet_type = bet["bet_type"]
        home_team = bet.get("home_team", "")
        away_team = bet.get("away_team", "")

        result = "loss"  # default

        if bet_type == "moneyline":
            # Determine which team was picked
            if _team_matches(pick, home_team):
                if home_score > away_score:
                    result = "win"
                elif home_score == away_score:
                    result = "push"
            elif _team_matches(pick, away_team):
                if away_score > home_score:
                    result = "win"
                elif home_score == away_score:
                    result = "push"

        elif bet_type == "spread":
            spread_line = bet.get("spread_line")
            if spread_line is not None:
                # Determine if pick is home or away
                if _team_matches(pick, home_team):
                    adjusted = home_score + spread_line
                    if adjusted > away_score:
                        result = "win"
                    elif adjusted == away_score:
                        result = "push"
                elif _team_matches(pick, away_team):
                    # Away spread is the inverse
                    adjusted = away_score + (-spread_line)
                    if adjusted > home_score:
                        result = "win"
                    elif adjusted == home_score:
                        result = "push"

        elif bet_type == "total":
            total_line = bet.get("total_line")
            if total_line is not None:
                actual_total = home_score + away_score
                pick_lower = pick.lower()
                if "over" in pick_lower:
                    if actual_total > total_line:
                        result = "win"
                    elif actual_total == total_line:
                        result = "push"
                elif "under" in pick_lower:
                    if actual_total < total_line:
                        result = "win"
                    elif actual_total == total_line:
                        result = "push"

        # Calculate P&L
        if result == "win":
            pnl = bet["potential_win"]
        elif result == "loss":
            pnl = -bet["stake"]
        else:
            pnl = 0.0

        conn.execute("""
            UPDATE bet_tracker
            SET result = ?, actual_pnl = ?, home_score = ?, away_score = ?,
                settled_at = datetime('now')
            WHERE id = ?
        """, (result, pnl, home_score, away_score, bet_id))

        bet.update({"result": result, "actual_pnl": pnl,
                     "home_score": home_score, "away_score": away_score})
        return bet


def _team_matches(pick: str, team_name: str) -> bool:
    """Check if the pick string likely refers to this team.

    Handles cases like 'Detroit Pistons -3.5' matching 'Detroit Pistons',
    or 'Pistons' matching 'Detroit Pistons'.
    """
    if not team_name:
        return False
    pick_lower = pick.lower().strip()
    team_lower = team_name.lower().strip()
    # Exact or prefix match
    if pick_lower.startswith(team_lower):
        return True
    # Team name is contained in pick
    if team_lower in pick_lower:
        return True
    # Last word of team name (e.g. "Pistons") in pick
    team_last = team_lower.split()[-1] if team_lower else ""
    if team_last and team_last in pick_lower:
        return True
    return False
