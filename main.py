import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response

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


@app.route("/")
def index():
    count = database.get_trade_count()
    fetch_str = last_fetch_time.strftime("%Y-%m-%d %H:%M UTC") if last_fetch_time else "Never"
    return (
        f"<h1>{config.FEED_TITLE}</h1>"
        f"<p>Tracking <strong>{count}</strong> trades from House &amp; Senate.</p>"
        f"<p>Last fetch: {fetch_str}</p>"
        f"<p>Poll interval: every {config.POLL_INTERVAL_HOURS} hours</p>"
        f'<p>RSS Feed: <a href="/feed">/feed</a></p>'
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
