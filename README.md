# Sports Arbitrage Finder

A local Python application that monitors live odds across multiple sportsbooks and surfaces **arbitrage opportunities** — situations where you can bet both sides of an event at different books and guarantee a profit regardless of the outcome.

## How It Works

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│ The Odds API │────▶│  Arbitrage Engine │────▶│  Web Dashboard│
│ (live odds)  │     │  (detect + calc)  │     │  (FastAPI)    │
└──────────────┘     └──────────────────┘     └───────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │    SQLite DB     │
                     │ (history + odds) │
                     └──────────────────┘
```

1. **Pulls live odds** from 30+ US sportsbooks via [The Odds API](https://the-odds-api.com)
2. **Scans every event** — for each market, finds the best price per outcome across all books
3. **Detects arbitrage** when combined implied probabilities dip below 100%
4. **Shows you exactly** where to bet, at what odds, and how much to stake for guaranteed profit
5. **Persists history** in a local SQLite database so you can track patterns

## Sports Covered

| Sport | API Key | Season |
|-------|---------|--------|
| 🏈 NFL | `americanfootball_nfl` | Sep – Feb |
| 🏀 NBA | `basketball_nba` | Oct – Jun |
| ⚾ MLB | `baseball_mlb` | Mar – Oct |
| 🏒 NHL | `icehockey_nhl` | Oct – Jun |

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get a free API key

Sign up at [the-odds-api.com](https://the-odds-api.com) (free tier = 500 requests/month).

Add your key to `.env`:

```bash
ODDS_API_KEY=your_key_here
```

### 3. Run

```bash
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

### Alternative: Docker

```bash
# Add your API key to .env first, then:
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Open **http://localhost:8000**. The SQLite database is persisted in a Docker volume so it survives container restarts.

## Dashboard

The web dashboard shows:

- **Live arbitrage opportunities** sorted by profit %
- **Bet breakdown** — which outcome to bet at which sportsbook
- **Stake calculator** — enter your bankroll and see exact dollar amounts per leg
- **Sport filters** — focus on NFL, NBA, MLB, or NHL
- **Auto-refresh** — odds update every 5 minutes (configurable)
- **API usage tracker** — see how many requests remain this month

## Configuration

All settings live in `.env` (see `.env.example` for docs):

| Variable | Default | Description |
|----------|---------|-------------|
| `ODDS_API_KEY` | — | Your API key from the-odds-api.com |
| `ODDS_FORMAT` | `american` | `american`, `decimal`, or `iso` |
| `MARKETS` | `h2h` | `h2h` (moneyline), `spreads`, `totals` |
| `REGIONS` | `us,us2` | Bookmaker regions to include |
| `MIN_PROFIT_PCT` | `0.0` | Minimum arb profit % to display |
| `REFRESH_INTERVAL` | `300` | Seconds between auto-refreshes (0 = manual) |
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8000` | Server port |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Web dashboard |
| `GET`  | `/api/arbitrage` | Current live arbitrage opportunities |
| `GET`  | `/api/arbitrage/history` | Historical arb opportunities |
| `GET`  | `/api/odds?sport=NFL` | Latest odds snapshot |
| `POST` | `/api/refresh` | Manually trigger odds refresh |
| `GET`  | `/api/status` | App status, config, API usage |
| `GET`  | `/api/sports` | Configured sports |

## Understanding Arbitrage

An arbitrage opportunity exists when different sportsbooks disagree on odds enough that you can cover all outcomes and guarantee profit.

**Example:** Team A vs Team B moneyline

| Outcome | Book | American Odds | Implied Prob |
|---------|------|:------------:|:------------:|
| Team A  | BookA | +150 | 40.0% |
| Team B  | BookB | +120 | 45.45% |
| **Total** | | | **85.45%** |

Since 85.45% < 100%, this is an arb. Profit = `(1/0.8545 - 1) = 17.03%`.

On a $100 bankroll:
- Bet $46.81 on Team A at BookA (+150)
- Bet $53.19 on Team B at BookB (+120)
- **Guaranteed return ≈ $117.03** no matter who wins

## Project Structure

```
sports/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + routes
│   ├── config.py          # Settings from .env
│   ├── database.py        # SQLite persistence
│   ├── models.py          # Pydantic data models
│   ├── odds_client.py     # The Odds API client
│   ├── arbitrage.py       # Arbitrage detection engine
│   ├── scheduler.py       # Background refresh loop
│   └── templates/
│       └── dashboard.html # Web dashboard (HTML/CSS/JS)
├── data/                  # SQLite database (auto-created)
├── .env                   # Your local config
├── .env.example           # Config documentation
├── Dockerfile             # Container image definition
├── docker-compose.yml     # One-command Docker startup
├── .dockerignore
├── requirements.txt
├── run.py                 # Entry point
└── README.md
```

## Tips

- **Arbs are rare and fleeting** — they typically last seconds to minutes before books adjust
- **Start with `h2h` (moneyline)** — simplest market with clearest arb math
- **Add `spreads,totals`** to `MARKETS` in `.env` for more opportunities
- **Lower `MIN_PROFIT_PCT`** to see more (smaller) opportunities
- **Watch your API quota** — 500 free requests/month ≈ 16/day ≈ 1 every 90 min

## License

MIT
