# ── Sports Arbitrage Finder ───────────────────────────────────────────
# Multi-stage build for a slim production image.

# ---------- build stage ----------
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- runtime stage ----------
FROM python:3.13-slim

LABEL maintainer="msfttoler"
LABEL description="Sports Arbitrage Finder – detect risk-free betting opportunities across sportsbooks"

# Non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY run.py .

# Create data directory for SQLite (will be a volume mount point)
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

# Default environment – override via docker run -e or docker-compose
ENV ODDS_API_KEY="" \
    ODDS_FORMAT="american" \
    MARKETS="h2h" \
    REGIONS="us,us2" \
    MIN_PROFIT_PCT="0.0" \
    REFRESH_INTERVAL="300" \
    HOST="0.0.0.0" \
    PORT="8000" \
    DB_PATH="/app/data/arbitrage.db" \
    RELOAD="false"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

CMD ["python", "run.py"]
