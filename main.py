import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, render_template_string, request
from urllib.parse import unquote

import config
import database
import feed
import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
last_fetch_time = None


def _check_auth():
    if not config.API_KEY:
        return True
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and auth_header[7:] == config.API_KEY:
        return True
    if request.args.get("key") == config.API_KEY:
        return True
    return False


@app.before_request
def require_auth():
    if not _check_auth():
        return Response(
            "Unauthorized. Provide API key via Authorization header or ?key= param.",
            status=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


def fetch_and_store():
    global last_fetch_time
    logger.info("Starting trade fetch...")
    trades = scraper.fetch_all_trades()
    if not trades:
        logger.warning("No trades fetched")
        return

    existing_ids = database.get_existing_ids()
    new_trades = [t for t in trades if t["id"] not in existing_ids]

    if new_trades:
        database.insert_trades(new_trades)
        logger.info("Stored %d new trades", len(new_trades))
    else:
        logger.info("No new trades found")

    last_fetch_time = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Shared layout + styles
# ---------------------------------------------------------------------------

LAYOUT_TOP = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ page_title }} - Politician Trade Tracker</title>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #f0f2f5; color: #212529; }

    /* --- Navbar --- */
    .navbar { background: #1a1a2e; padding: 0 24px; display: flex; align-items: center;
              box-shadow: 0 2px 8px rgba(0,0,0,0.15); position: sticky; top: 0; z-index: 100; }
    .navbar .brand { color: #fff; font-weight: 700; font-size: 1.1em; padding: 14px 0;
                     text-decoration: none; margin-right: 32px; }
    .navbar .nav-links { display: flex; gap: 0; }
    .navbar .nav-links a { color: #a0aec0; text-decoration: none; padding: 14px 16px;
                           font-size: 0.9em; font-weight: 500; border-bottom: 3px solid transparent;
                           transition: all 0.15s; }
    .navbar .nav-links a:hover { color: #fff; background: rgba(255,255,255,0.05); }
    .navbar .nav-links a.active { color: #fff; border-bottom-color: #4dabf7; }
    .navbar .nav-right { margin-left: auto; display: flex; align-items: center; gap: 16px; }
    .navbar .nav-right a { color: #a0aec0; text-decoration: none; font-size: 0.85em; }
    .navbar .nav-right a:hover { color: #fff; }
    .navbar .status { color: #6c757d; font-size: 0.75em; }

    /* --- Content --- */
    .container { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }
    h1 { margin-bottom: 4px; font-size: 1.5em; }
    .subtitle { color: #6c757d; margin-bottom: 20px; font-size: 0.9em; }

    /* --- Tables --- */
    table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-top: 12px; }
    th { background: #343a40; color: #fff; text-align: left; padding: 10px 12px; font-size: 0.8em;
         text-transform: uppercase; letter-spacing: 0.5px; }
    td { padding: 9px 12px; border-bottom: 1px solid #e9ecef; font-size: 0.85em; }
    tr:hover td { background: #f8f9fa; }
    .empty-state { text-align: center; padding: 48px 20px; color: #6c757d; }
    .empty-state p { margin-top: 8px; font-size: 0.9em; }

    /* --- Links --- */
    a.name-link { color: #0d6efd; text-decoration: none; font-weight: 500; }
    a.name-link:hover { text-decoration: underline; }

    /* --- Badges --- */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
             font-size: 0.75em; font-weight: 600; }
    .buy { background: #d4edda; color: #155724; }
    .sell { background: #f8d7da; color: #721c24; }
    .other { background: #e2e3e5; color: #383d41; }
    .exchange { background: #fff3cd; color: #856404; }

    /* --- Stat cards --- */
    .stats { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .stat-card { background: #fff; border-radius: 8px; padding: 16px 20px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 160px; }
    .stat-card .label { font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.5px;
                        color: #6c757d; margin-bottom: 4px; }
    .stat-card .value { font-size: 1.5em; font-weight: 700; }

    /* --- Sections --- */
    h2 { margin: 24px 0 4px; font-size: 1.15em; }
    .section-note { color: #6c757d; font-size: 0.85em; margin-bottom: 4px; }
    .back-link { display: inline-block; margin-bottom: 12px; color: #0d6efd;
                 text-decoration: none; font-size: 0.9em; }
    .back-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="navbar">
    <a class="brand" href="/{{ key_param }}">TradeTracker</a>
    <div class="nav-links">
        <a href="/{{ key_param }}" class="{{ 'active' if active_nav == 'trades' else '' }}">Recent Trades</a>
        <a href="/portfolios{{ key_param }}" class="{{ 'active' if active_nav == 'portfolios' else '' }}">Portfolios</a>
    </div>
    <div class="nav-right">
        <a href="/feed{{ key_param }}">RSS Feed</a>
        <span class="status">Last fetch: {{ fetch_str }}</span>
    </div>
</div>
<div class="container">
"""

LAYOUT_BOTTOM = """
</div>
</body>
</html>
"""


def _page(content_template, **kwargs):
    """Render a page by sandwiching content between layout top and bottom."""
    full = LAYOUT_TOP + content_template + LAYOUT_BOTTOM
    return render_template_string(full, **kwargs)


INDEX_CONTENT = """
<h1>Recent Trades</h1>
<p class="subtitle">Trades disclosed in the last 7 days</p>

<div class="stats">
    <div class="stat-card">
        <div class="label">Trades (7 days)</div>
        <div class="value">{{ trades | length }}</div>
    </div>
    <div class="stat-card">
        <div class="label">Total in Database</div>
        <div class="value">{{ total_count }}</div>
    </div>
    <div class="stat-card">
        <div class="label">Politicians Active</div>
        <div class="value">{{ active_politicians }}</div>
    </div>
</div>

{% if trades %}
<table>
<thead>
<tr>
    <th>Politician</th><th>Chamber</th><th>Ticker</th><th>Asset</th>
    <th>Type</th><th>Amount</th><th>Trade Date</th><th>Disclosed</th>
</tr>
</thead>
<tbody>
{% for t in trades %}
<tr>
    <td><a class="name-link" href="/politician/{{ t.politician | urlencode }}{{ key_param }}">{{ t.politician }}</a></td>
    <td>{{ t.chamber }}</td>
    <td><strong>{{ t.ticker or 'N/A' }}</strong></td>
    <td>{{ t.asset_description[:45] ~ '...' if t.asset_description and t.asset_description|length > 45 else t.asset_description or '' }}</td>
    <td><span class="badge {{ badge_class(t.trade_type) }}">{{ badge_label(t.trade_type) }}</span></td>
    <td>{{ t.amount or '' }}</td>
    <td>{{ t.transaction_date or '' }}</td>
    <td>{{ t.disclosure_date or '' }}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<div class="empty-state">
    <h2>No trades in the last 7 days</h2>
    <p>New trades will appear here as they are disclosed. Data is fetched every {{ poll_hours }} hours.</p>
</div>
{% endif %}
"""

PORTFOLIOS_CONTENT = """
<h1>Active Portfolios</h1>
<p class="subtitle">All politicians with recorded trades, sorted by most recent activity</p>

<div class="stats">
    <div class="stat-card">
        <div class="label">Politicians Tracked</div>
        <div class="value">{{ portfolios | length }}</div>
    </div>
    <div class="stat-card">
        <div class="label">Total Trades</div>
        <div class="value">{{ total_count }}</div>
    </div>
</div>

{% if portfolios %}
<table>
<thead>
<tr>
    <th>Politician</th><th>Chamber</th><th>Tickers</th>
    <th>Buys</th><th>Sells</th><th>Total Trades</th><th>Last Disclosed</th>
</tr>
</thead>
<tbody>
{% for p in portfolios %}
<tr>
    <td><a class="name-link" href="/politician/{{ p.politician | urlencode }}{{ key_param }}">{{ p.politician }}</a></td>
    <td>{{ p.chamber }}</td>
    <td>{{ p.unique_tickers }}</td>
    <td>{{ p.buys }}</td>
    <td>{{ p.sells }}</td>
    <td>{{ p.total_trades }}</td>
    <td>{{ p.last_disclosure or '' }}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<div class="empty-state">
    <h2>No portfolio data yet</h2>
    <p>Trade data will appear after the first successful fetch.</p>
</div>
{% endif %}
"""

POLITICIAN_CONTENT = """
<a class="back-link" href="/portfolios{{ key_param }}">&larr; Back to Portfolios</a>
<h1>{{ name }}</h1>
<p class="subtitle">{{ chamber }} &middot; {{ trade_count }} total trades</p>

<h2>Holdings Summary</h2>
<p class="section-note">Net activity per ticker based on all recorded trades</p>
{% if holdings %}
<table>
<thead>
<tr><th>Ticker</th><th>Asset</th><th>Buys</th><th>Sells</th><th>Net</th><th>Last Trade</th></tr>
</thead>
<tbody>
{% for h in holdings %}
<tr>
    <td><strong>{{ h.ticker }}</strong></td>
    <td>{{ h.asset_description[:50] ~ '...' if h.asset_description and h.asset_description|length > 50 else h.asset_description or '' }}</td>
    <td>{{ h.buys }}</td>
    <td>{{ h.sells }}</td>
    <td>{{ h.buys - h.sells }}</td>
    <td>{{ h.last_trade_date or '' }}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<p class="section-note">No ticker-level holdings data available.</p>
{% endif %}

<h2>All Trades</h2>
<table>
<thead>
<tr>
    <th>Ticker</th><th>Asset</th><th>Type</th><th>Amount</th>
    <th>Owner</th><th>Trade Date</th><th>Disclosed</th><th>Filing</th>
</tr>
</thead>
<tbody>
{% for t in trades %}
<tr>
    <td><strong>{{ t.ticker or 'N/A' }}</strong></td>
    <td>{{ t.asset_description[:45] ~ '...' if t.asset_description and t.asset_description|length > 45 else t.asset_description or '' }}</td>
    <td><span class="badge {{ badge_class(t.trade_type) }}">{{ badge_label(t.trade_type) }}</span></td>
    <td>{{ t.amount or '' }}</td>
    <td>{{ t.owner or '' }}</td>
    <td>{{ t.transaction_date or '' }}</td>
    <td>{{ t.disclosure_date or '' }}</td>
    <td>{% if t.ptr_link %}<a href="{{ t.ptr_link }}" target="_blank">View</a>{% endif %}</td>
</tr>
{% endfor %}
</tbody>
</table>
"""

NOT_FOUND_CONTENT = """
<div class="empty-state">
    <h2>No trades found for {{ name }}</h2>
    <p><a href="/portfolios{{ key_param }}">Back to Portfolios</a></p>
</div>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade_badge(trade_type):
    t = (trade_type or "").lower()
    if "purchase" in t or "buy" in t:
        return "buy", "BUY"
    elif "sale" in t or "sell" in t:
        return "sell", "SELL"
    elif "exchange" in t:
        return "exchange", "EXCHANGE"
    return "other", trade_type or "N/A"


def _key_param():
    key = request.args.get("key")
    return f"?key={key}" if key else ""


def _common_vars(active_nav):
    fetch_str = last_fetch_time.strftime("%Y-%m-%d %H:%M UTC") if last_fetch_time else "Never"
    return {
        "key_param": _key_param(),
        "fetch_str": fetch_str,
        "active_nav": active_nav,
        "badge_class": lambda t: _trade_badge(t)[0],
        "badge_label": lambda t: _trade_badge(t)[1],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    trades = database.get_trades_since(days=7)
    active_politicians = len({t["politician"] for t in trades})
    return _page(
        INDEX_CONTENT,
        page_title="Recent Trades",
        trades=trades,
        total_count=database.get_trade_count(),
        active_politicians=active_politicians,
        poll_hours=config.POLL_INTERVAL_HOURS,
        **_common_vars("trades"),
    )


@app.route("/portfolios")
def portfolios():
    return _page(
        PORTFOLIOS_CONTENT,
        page_title="Portfolios",
        portfolios=database.get_active_portfolios(),
        total_count=database.get_trade_count(),
        **_common_vars("portfolios"),
    )


@app.route("/politician/<path:name>")
def politician(name):
    name = unquote(name)
    trades = database.get_trades_by_politician(name)
    if not trades:
        return _page(
            NOT_FOUND_CONTENT,
            page_title="Not Found",
            name=name,
            **_common_vars("portfolios"),
        ), 404
    holdings = database.get_holdings_by_politician(name)
    chamber = trades[0]["chamber"] if trades else ""
    return _page(
        POLITICIAN_CONTENT,
        page_title=name,
        name=name,
        chamber=chamber,
        trade_count=len(trades),
        trades=trades,
        holdings=holdings,
        **_common_vars("portfolios"),
    )


@app.route("/feed")
def rss_feed():
    trades = database.get_recent_trades()
    rss_xml = feed.generate_feed(trades)
    return Response(rss_xml, mimetype="application/rss+xml")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def main():
    database.init_db()

    if config.API_KEY:
        logger.info("Authentication ENABLED")
        logger.info("  Web UI: http://%s:%d/?key=%s", config.HOST, config.PORT, config.API_KEY)
        logger.info("  RSS:    http://%s:%d/feed?key=%s", config.HOST, config.PORT, config.API_KEY)
    else:
        logger.info("Authentication DISABLED (set TRADETRACKER_API_KEY to enable)")

    # Run initial fetch — don't let failure prevent server from starting
    try:
        fetch_and_store()
    except Exception as e:
        logger.error("Initial fetch failed (will retry on schedule): %s", e)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_and_store,
        "interval",
        hours=config.POLL_INTERVAL_HOURS,
        id="fetch_trades",
    )
    scheduler.start()
    logger.info("Scheduler started (every %d hours)", config.POLL_INTERVAL_HOURS)

    logger.info("Starting server on %s:%d", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
