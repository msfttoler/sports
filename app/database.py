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
