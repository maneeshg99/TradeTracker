# TradeTracker

Monitor US politician stock trades (House & Senate) and get updates via a web dashboard and RSS feed.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/maneeshg99/TradeTracker.git
cd TradeTracker

# 2. Install Python dependencies (requires Python 3.10+)
pip install -r requirements.txt

# 3. Generate an API key
python -c "import config; print(config.generate_api_key())"
# Save the output — you'll need it below

# 4. Run it
TRADETRACKER_API_KEY=<your-key-here> python main.py
```

On first run it fetches all trades (takes ~30s), then the server starts on **http://localhost:5050**.

Open in your browser: `http://localhost:5050/?key=<your-key-here>`

## Features

- **Trades table** — sortable list of recent politician stock trades
- **Politician pages** — click any name to see their holdings summary and full trade history
- **RSS feed** — subscribe in any reader for new trade alerts
- **API key auth** — simple token-based auth for remote access
- **Auto-refresh** — re-fetches data every 12 hours (configurable)

## Pages

| URL | Description |
|---|---|
| `/` | Dashboard with recent trades table |
| `/politician/<name>` | Holdings + trade history for a politician |
| `/feed` | RSS 2.0 feed of latest trades |

When auth is enabled, append `?key=<your-key>` to any URL. Links within the UI carry the key automatically.

## Authentication

Set `TRADETRACKER_API_KEY` to require a key on all requests. Two ways to authenticate:

```
# Query parameter (browsers, RSS readers)
http://localhost:5050/?key=your-secret-key
http://localhost:5050/feed?key=your-secret-key

# HTTP header (API clients, curl)
curl -H "Authorization: Bearer your-secret-key" http://localhost:5050/
```

If `TRADETRACKER_API_KEY` is not set, auth is disabled (fine for local-only use).

## Run as a System Service (Linux)

This keeps TradeTracker running 24/7 and auto-starts on boot.

### Step 1: Edit the service file

```bash
nano tradetracker@.service
```

Change `TRADETRACKER_API_KEY=CHANGE_ME` to your actual key. Adjust other env vars if needed.

### Step 2: Install the service

```bash
sudo cp tradetracker@.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Step 3: Enable and start

Replace `YOUR_USERNAME` with your Linux username (e.g., `john`):

```bash
sudo systemctl enable tradetracker@YOUR_USERNAME   # start on boot
sudo systemctl start tradetracker@YOUR_USERNAME     # start now
```

### Managing the service

```bash
# Check status
sudo systemctl status tradetracker@YOUR_USERNAME

# View live logs
sudo journalctl -u tradetracker@YOUR_USERNAME -f

# Restart after code changes
sudo systemctl restart tradetracker@YOUR_USERNAME

# Stop
sudo systemctl stop tradetracker@YOUR_USERNAME

# Disable auto-start
sudo systemctl disable tradetracker@YOUR_USERNAME
```

## Run on macOS (launchd)

Create `~/Library/LaunchAgents/com.tradetracker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradetracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/TradeTracker/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/TradeTracker</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TRADETRACKER_API_KEY</key>
        <string>your-key-here</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/tradetracker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/tradetracker.err</string>
</dict>
</plist>
```

Then:
```bash
# Fix the paths in the plist, then:
launchctl load ~/Library/LaunchAgents/com.tradetracker.plist

# To stop:
launchctl unload ~/Library/LaunchAgents/com.tradetracker.plist

# View logs:
tail -f /tmp/tradetracker.log
```

## Remote Access with Tailscale

Access TradeTracker from your phone, laptop, or work computer — securely, with no port forwarding.

### Step 1: Install Tailscale

Install on both your server and any device you want to access from:
- https://tailscale.com/download

It's free for personal use (up to 100 devices).

### Step 2: Start Tailscale

```bash
# On your server
sudo tailscale up
tailscale ip   # note the 100.x.y.z address
```

### Step 3: Access from anywhere

From any device on your Tailscale network:
```
http://100.x.y.z:5050/?key=your-secret-key
```

For RSS readers on your phone, use this URL:
```
http://100.x.y.z:5050/feed?key=your-secret-key
```

All traffic is encrypted end-to-end. Nothing is exposed to the public internet.

## Configuration

All settings use environment variables — no config files to manage.

| Variable | Default | Description |
|---|---|---|
| `TRADETRACKER_API_KEY` | *(empty)* | API key for auth (disabled if unset) |
| `TRADETRACKER_HOST` | `0.0.0.0` | Server bind address |
| `TRADETRACKER_PORT` | `5050` | Server port |
| `TRADETRACKER_POLL_HOURS` | `12` | Hours between data fetches |
| `TRADETRACKER_FEED_LIMIT` | `100` | Max items in RSS feed |

Example with custom settings:
```bash
TRADETRACKER_API_KEY=mykey TRADETRACKER_PORT=8080 TRADETRACKER_POLL_HOURS=6 python main.py
```

## Data Sources

Trade data comes from free, public sources based on [STOCK Act](https://www.congress.gov/bill/112th-congress/senate-bill/2038) disclosures:

- [House Stock Watcher](https://housestockwatcher.com/) — House representatives
- [Senate Stock Watcher](https://senatestockwatcher.com/) — Senators

No API keys required. No paid subscriptions. Data is updated as new disclosures are filed.

## Project Structure

```
TradeTracker/
├── main.py                # Entry point: Flask server + scheduler
├── scraper.py             # Fetches trades from House/Senate data sources
├── database.py            # SQLite persistence and queries
├── feed.py                # RSS feed generation
├── config.py              # Configuration via environment variables
├── requirements.txt       # Python dependencies
├── tradetracker@.service  # systemd service template (Linux)
└── data/
    └── trades.db          # SQLite database (created at runtime)
```

## Troubleshooting

**"No trades fetched" on startup** — The data sources may be temporarily unavailable. The scheduler will retry at the next interval. Check your internet connection.

**Port already in use** — Change the port: `TRADETRACKER_PORT=8080 python main.py`

**Permission denied on systemd** — Make sure you used `sudo` for `cp` and `systemctl` commands.

**RSS reader can't connect** — If using auth, make sure the feed URL includes `?key=...`. If accessing remotely, make sure Tailscale is running on both devices.
