# TradeTracker

Monitor US politician stock trades (House & Senate) and get updates via RSS feed.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Without authentication (local-only use)
python main.py

# With authentication (recommended for remote access)
TRADETRACKER_API_KEY=your-secret-key python main.py
```

This starts a local web server on port 5050 and fetches trade data every 12 hours.

- **Trades table**: http://localhost:5050/
- **Politician holdings**: http://localhost:5050/politician/Nancy%20Pelosi
- **RSS feed**: http://localhost:5050/feed

Subscribe to the RSS feed URL in any RSS reader (Thunderbird, Feedly, NetNewsWire, etc.).

## Authentication

Set `TRADETRACKER_API_KEY` to enable API key authentication. When enabled, all requests must include the key via:

- **Query parameter**: `http://localhost:5050/?key=your-secret-key`
- **Authorization header**: `Authorization: Bearer your-secret-key`

The key propagates automatically through links in the web UI. For RSS readers, use the `?key=` URL format.

Generate a random key:
```bash
python -c "import config; print(config.generate_api_key())"
```

## Run as a System Service

To auto-start on boot using systemd:

```bash
# 1. Edit the service file and set your API key
nano tradetracker@.service

# 2. Copy to systemd
sudo cp tradetracker@.service /etc/systemd/system/

# 3. Enable and start (replace YOUR_USERNAME with your Linux user)
sudo systemctl enable --now tradetracker@YOUR_USERNAME
```

Check status:
```bash
sudo systemctl status tradetracker@YOUR_USERNAME
sudo journalctl -u tradetracker@YOUR_USERNAME -f
```

## Remote Access with Tailscale

For secure access from anywhere (phone, work, etc.):

1. Install [Tailscale](https://tailscale.com/) on your server and devices (free for personal use)
2. Start TradeTracker with an API key
3. Access via your Tailscale IP: `http://100.x.y.z:5050/?key=your-secret-key`

No port forwarding, no public exposure - traffic is encrypted end-to-end.

## Configuration

Override defaults with environment variables:

| Variable | Default | Description |
|---|---|---|
| `TRADETRACKER_HOST` | `0.0.0.0` | Server bind address |
| `TRADETRACKER_PORT` | `5050` | Server port |
| `TRADETRACKER_API_KEY` | *(empty)* | API key for auth (disabled if unset) |
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
4. Web UI shows a trades table with clickable politician names leading to holdings pages
5. RSS feed is generated on-the-fly from the most recent trades
6. Scheduler re-fetches every 12 hours (configurable)
