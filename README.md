# TradeTracker

Monitor US politician stock trades (House & Senate) and get updates via RSS feed.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

This starts a local web server on port 5050 and fetches trade data every 12 hours.

- **Status page**: http://localhost:5050/
- **RSS feed**: http://localhost:5050/feed

Subscribe to the RSS feed URL in any RSS reader (Thunderbird, Feedly, NetNewsWire, etc.).

## Configuration

Override defaults with environment variables:

| Variable | Default | Description |
|---|---|---|
| `TRADETRACKER_HOST` | `0.0.0.0` | Server bind address |
| `TRADETRACKER_PORT` | `5050` | Server port |
| `TRADETRACKER_POLL_HOURS` | `12` | Hours between data fetches |
| `TRADETRACKER_FEED_LIMIT` | `100` | Max items in RSS feed |

## Data Sources

Trade data is pulled from free, public sources based on STOCK Act disclosures:

- [House Stock Watcher](https://housestockwatcher.com/) - House representatives
- [Senate Stock Watcher](https://senatestockwatcher.com/) - Senators

## How It Works

1. On startup, fetches all known trades from both House and Senate data sources
2. Stores trades in a local SQLite database (`data/trades.db`)
3. New trades are detected by deduplication (hash of key fields)
4. RSS feed is generated on-the-fly from the most recent trades
5. Scheduler re-fetches every 12 hours (configurable)
