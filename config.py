import os
import secrets

# Server
HOST = os.environ.get("TRADETRACKER_HOST", "0.0.0.0")
PORT = int(os.environ.get("TRADETRACKER_PORT", "5050"))

# Authentication
# Set TRADETRACKER_API_KEY to enable auth. If unset, auth is disabled.
API_KEY = os.environ.get("TRADETRACKER_API_KEY", "")

# Scheduler
POLL_INTERVAL_HOURS = int(os.environ.get("TRADETRACKER_POLL_HOURS", "12"))

# Database
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "trades.db")

# Feed
FEED_TITLE = "Politician Trade Tracker"
FEED_DESCRIPTION = "Latest stock trades by US politicians (House & Senate)"
FEED_LIMIT = int(os.environ.get("TRADETRACKER_FEED_LIMIT", "100"))

# Data sources
HOUSE_TRADES_URL = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
SENATE_TRADES_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"

# HTTP
REQUEST_TIMEOUT = 60
USER_AGENT = "TradeTracker/1.0 (Personal RSS Feed Generator)"


def generate_api_key():
    """Helper to generate a random API key."""
    return secrets.token_urlsafe(32)
