import hashlib
import logging

import requests

import config

logger = logging.getLogger(__name__)


def _make_id(politician, ticker, transaction_date, trade_type, amount):
    raw = f"{politician}|{ticker}|{transaction_date}|{trade_type}|{amount}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_json(url):
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_house_trades():
    logger.info("Fetching House trades...")
    try:
        data = _get_json(config.HOUSE_TRADES_URL)
    except Exception as e:
        logger.error("Failed to fetch House trades: %s", e)
        return []

    trades = []
    for t in data:
        ticker = t.get("ticker", "")
        if ticker == "--":
            ticker = None
        owner = t.get("owner", "")
        if owner == "--":
            owner = None
        trade = {
            "id": _make_id(
                t.get("representative", ""),
                ticker or "",
                t.get("transaction_date", ""),
                t.get("type", ""),
                t.get("amount", ""),
            ),
            "politician": t.get("representative", "Unknown"),
            "chamber": "House",
            "ticker": ticker,
            "asset_description": t.get("asset_description"),
            "trade_type": t.get("type", "unknown"),
            "amount": t.get("amount"),
            "transaction_date": t.get("transaction_date"),
            "disclosure_date": t.get("disclosure_date"),
            "owner": owner,
            "ptr_link": t.get("ptr_link"),
            "district": t.get("district"),
        }
        trades.append(trade)

    logger.info("Fetched %d House trades", len(trades))
    return trades


def fetch_senate_trades():
    logger.info("Fetching Senate trades...")
    try:
        data = _get_json(config.SENATE_TRADES_URL)
    except Exception as e:
        logger.error("Failed to fetch Senate trades: %s", e)
        return []

    trades = []
    for t in data:
        # Senate data is a flat array — each record has senator info + transaction
        politician = (t.get("first_name", "") + " " + t.get("last_name", "")).strip()
        politician = politician or "Unknown"
        ticker = t.get("ticker", "")
        if ticker == "--" or ticker == "N/A" or ticker == "":
            ticker = None
        owner = t.get("owner", "")
        if owner == "--":
            owner = None
        # Senate uses "date_recieved" (typo in source) as disclosure date
        disclosure_date = t.get("date_recieved") or t.get("disclosure_date")
        trade = {
            "id": _make_id(
                politician,
                ticker or "",
                t.get("transaction_date", ""),
                t.get("type", ""),
                t.get("amount", ""),
            ),
            "politician": politician,
            "chamber": "Senate",
            "ticker": ticker,
            "asset_description": t.get("asset_description"),
            "trade_type": t.get("type", "unknown"),
            "amount": t.get("amount"),
            "transaction_date": t.get("transaction_date"),
            "disclosure_date": disclosure_date,
            "owner": owner,
            "ptr_link": t.get("ptr_link"),
            "district": None,
        }
        trades.append(trade)

    logger.info("Fetched %d Senate trades", len(trades))
    return trades


def fetch_all_trades():
    house = fetch_house_trades()
    senate = fetch_senate_trades()
    return house + senate
