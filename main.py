import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, render_template_string
from urllib.parse import quote, unquote

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


BASE_STYLE = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           max-width: 1200px; margin: 0 auto; padding: 20px; background: #f8f9fa; color: #212529; }
    h1 { margin-bottom: 8px; }
    .meta { color: #6c757d; margin-bottom: 20px; font-size: 0.9em; }
    .meta a { color: #0d6efd; text-decoration: none; }
    .meta a:hover { text-decoration: underline; }
    nav { margin-bottom: 16px; font-size: 0.9em; }
    nav a { color: #0d6efd; text-decoration: none; }
    nav a:hover { text-decoration: underline; }
    table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px;
            overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-top: 12px; }
    th { background: #343a40; color: #fff; text-align: left; padding: 10px 12px; font-size: 0.85em; }
    td { padding: 8px 12px; border-bottom: 1px solid #e9ecef; font-size: 0.85em; }
    tr:hover td { background: #f1f3f5; }
    a.politician { color: #0d6efd; text-decoration: none; font-weight: 500; }
    a.politician:hover { text-decoration: underline; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; }
    .buy { background: #d4edda; color: #155724; }
    .sell { background: #f8d7da; color: #721c24; }
    .other { background: #e2e3e5; color: #383d41; }
    .exchange { background: #fff3cd; color: #856404; }
    h2 { margin: 20px 0 4px; }
    .section-note { color: #6c757d; font-size: 0.85em; margin-bottom: 8px; }
</style>
"""


def _trade_badge(trade_type):
    t = (trade_type or "").lower()
    if "purchase" in t or "buy" in t:
        return "buy", "BUY"
    elif "sale" in t or "sell" in t:
        return "sell", "SELL"
    elif "exchange" in t:
        return "exchange", "EXCHANGE"
    return "other", trade_type or "N/A"


INDEX_TEMPLATE = (
    "<!DOCTYPE html><html><head><title>{{ title }}</title>"
    + BASE_STYLE
    + "</head><body>"
    + """
<h1>{{ title }}</h1>
<p class="meta">
    Tracking <strong>{{ count }}</strong> trades from House &amp; Senate.
    Last fetch: {{ fetch_str }}.
    Poll interval: every {{ poll_hours }} hours.
    <a href="/feed">RSS Feed</a>
</p>

<h2>Recent Trades</h2>
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
    <td><a class="politician" href="/politician/{{ t.politician | urlencode }}">{{ t.politician }}</a></td>
    <td>{{ t.chamber }}</td>
    <td>{{ t.ticker or 'N/A' }}</td>
    <td>{{ t.asset_description[:40] ~ '...' if t.asset_description and t.asset_description|length > 40 else t.asset_description or '' }}</td>
    <td><span class="badge {{ badge_class(t.trade_type) }}">{{ badge_label(t.trade_type) }}</span></td>
    <td>{{ t.amount or '' }}</td>
    <td>{{ t.transaction_date or '' }}</td>
    <td>{{ t.disclosure_date or '' }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</body></html>
"""
)

POLITICIAN_TEMPLATE = (
    "<!DOCTYPE html><html><head><title>{{ name }} - Trades</title>"
    + BASE_STYLE
    + "</head><body>"
    + """
<nav><a href="/">&larr; Back to all trades</a></nav>
<h1>{{ name }}</h1>
<p class="meta">{{ chamber }} &middot; {{ trade_count }} total trades</p>

<h2>Holdings Summary</h2>
<p class="section-note">Net activity per ticker based on all recorded trades.</p>
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
<p>No ticker-level holdings data available.</p>
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
    <td>{{ t.ticker or 'N/A' }}</td>
    <td>{{ t.asset_description[:40] ~ '...' if t.asset_description and t.asset_description|length > 40 else t.asset_description or '' }}</td>
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
</body></html>
"""
)


@app.route("/")
def index():
    count = database.get_trade_count()
    fetch_str = last_fetch_time.strftime("%Y-%m-%d %H:%M UTC") if last_fetch_time else "Never"
    trades = database.get_recent_trades()
    return render_template_string(
        INDEX_TEMPLATE,
        title=config.FEED_TITLE,
        count=count,
        fetch_str=fetch_str,
        poll_hours=config.POLL_INTERVAL_HOURS,
        trades=trades,
        badge_class=lambda t: _trade_badge(t)[0],
        badge_label=lambda t: _trade_badge(t)[1],
    )


@app.route("/politician/<path:name>")
def politician(name):
    name = unquote(name)
    trades = database.get_trades_by_politician(name)
    if not trades:
        return f"<h1>No trades found for {name}</h1><p><a href='/'>Back</a></p>", 404
    holdings = database.get_holdings_by_politician(name)
    chamber = trades[0]["chamber"] if trades else ""
    return render_template_string(
        POLITICIAN_TEMPLATE,
        name=name,
        chamber=chamber,
        trade_count=len(trades),
        trades=trades,
        holdings=holdings,
        badge_class=lambda t: _trade_badge(t)[0],
        badge_label=lambda t: _trade_badge(t)[1],
    )


@app.route("/feed")
def rss_feed():
    trades = database.get_recent_trades()
    rss_xml = feed.generate_feed(trades)
    return Response(rss_xml, mimetype="application/rss+xml")


def main():
    database.init_db()

    # Initial fetch
    fetch_and_store()

    # Schedule periodic fetches
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_and_store,
        "interval",
        hours=config.POLL_INTERVAL_HOURS,
        id="fetch_trades",
    )
    scheduler.start()
    logger.info("Scheduler started (every %d hours)", config.POLL_INTERVAL_HOURS)

    # Start web server
    logger.info("Starting server on %s:%d", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
