"""
Background scheduler that periodically refreshes odds and scans for arbitrage.
"""

import asyncio
import logging

from app.config import settings
from app.odds_client import OddsClient
from app.arbitrage import detect_arbitrage
from app.models import RefreshResult

logger = logging.getLogger(__name__)

# Global state
_refresh_task: asyncio.Task | None = None
_last_result: RefreshResult | None = None


async def refresh_odds() -> RefreshResult:
    """
    Fetch latest odds from all configured sports, detect arbitrage,
    and return a summary.
    """
    global _last_result
    result = RefreshResult()

    if not settings.has_api_key:
        result.errors.append("No ODDS_API_KEY configured. Add it to your .env file.")
        _last_result = result
        return result

    client = OddsClient()
    try:
        events, usage = await client.fetch_all_sports()
        result.events_fetched = len(events)
        result.sports_checked = list(settings.SPORT_KEYS.keys())

        if usage.get("remaining") is not None:
            result.api_requests_remaining = int(usage["remaining"])

        # Persist raw odds
        client.persist_events(events)

        # Detect arbitrage
        arbs = detect_arbitrage(events)
        result.arbitrage_found = len(arbs)

    except Exception as e:
        logger.error("Error during odds refresh: %s", e)
        result.errors.append(str(e))
    finally:
        await client.close()

    _last_result = result
    logger.info(
        "Refresh complete: %d events, %d arbs, API remaining: %s",
        result.events_fetched,
        result.arbitrage_found,
        result.api_requests_remaining,
    )
    return result


def get_last_result() -> RefreshResult | None:
    return _last_result


async def _scheduler_loop():
    """Background loop that refreshes odds on an interval."""
    while True:
        try:
            await refresh_odds()
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        await asyncio.sleep(settings.REFRESH_INTERVAL)


def start_scheduler():
    """Start the background refresh scheduler if interval > 0."""
    global _refresh_task
    if settings.REFRESH_INTERVAL > 0 and settings.has_api_key:
        loop = asyncio.get_running_loop()
        _refresh_task = loop.create_task(_scheduler_loop())
        logger.info("Scheduler started – refreshing every %ds", settings.REFRESH_INTERVAL)
    else:
        logger.info("Scheduler disabled (interval=0 or no API key)")


def stop_scheduler():
    global _refresh_task
    if _refresh_task:
        _refresh_task.cancel()
        _refresh_task = None
