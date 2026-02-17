"""
Entry point for the Sports Arbitrage Finder.

Run with:
    python run.py          # local dev (auto-reload on)
    docker compose up      # Docker (auto-reload off)
"""

import os

import uvicorn

from app.config import settings

if __name__ == "__main__":
    reload = os.getenv("RELOAD", "true").lower() in ("1", "true", "yes")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload,
    )
