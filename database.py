import os
import sqlite3
from datetime import datetime, timezone

import config


def _connect():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            politician TEXT NOT NULL,
            chamber TEXT NOT NULL,
            ticker TEXT,
            asset_description TEXT,
            trade_type TEXT NOT NULL,
            amount TEXT,
            transaction_date TEXT,
            disclosure_date TEXT,
            owner TEXT,
            ptr_link TEXT,
            district TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_disclosure_date
        ON trades (disclosure_date DESC)
    """)
    conn.commit()
    conn.close()


def get_existing_ids():
    conn = _connect()
    rows = conn.execute("SELECT id FROM trades").fetchall()
    conn.close()
    return {row["id"] for row in rows}


def insert_trades(trades):
    if not trades:
        return 0
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for t in trades:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO trades
                   (id, politician, chamber, ticker, asset_description, trade_type,
                    amount, transaction_date, disclosure_date, owner, ptr_link,
                    district, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t["id"], t["politician"], t["chamber"], t.get("ticker"),
                    t.get("asset_description"), t["trade_type"], t.get("amount"),
                    t.get("transaction_date"), t.get("disclosure_date"),
                    t.get("owner"), t.get("ptr_link"), t.get("district"), now,
                ),
            )
            if conn.total_changes:
                count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return count


def get_recent_trades(limit=None):
    limit = limit or config.FEED_LIMIT
    conn = _connect()
    rows = conn.execute(
        """SELECT * FROM trades
           ORDER BY disclosure_date DESC, created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_trade_count():
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    conn.close()
    return count


def get_politicians():
    conn = _connect()
    rows = conn.execute(
        """SELECT politician, chamber, COUNT(*) as trade_count
           FROM trades
           GROUP BY politician
           ORDER BY politician""",
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_trades_by_politician(name):
    conn = _connect()
    rows = conn.execute(
        """SELECT * FROM trades
           WHERE politician = ?
           ORDER BY disclosure_date DESC, created_at DESC""",
        (name,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_holdings_by_politician(name):
    """Compute net holdings: purchases add, sales subtract."""
    conn = _connect()
    rows = conn.execute(
        """SELECT ticker, asset_description, trade_type, amount,
                  transaction_date, disclosure_date, owner, ptr_link
           FROM trades
           WHERE politician = ? AND ticker IS NOT NULL
           ORDER BY transaction_date DESC""",
        (name,),
    ).fetchall()
    conn.close()

    holdings = {}
    for row in rows:
        row = dict(row)
        ticker = row["ticker"]
        if ticker not in holdings:
            holdings[ticker] = {
                "ticker": ticker,
                "asset_description": row["asset_description"],
                "buys": 0,
                "sells": 0,
                "last_trade_date": row["transaction_date"],
                "last_trade_type": row["trade_type"],
            }
        trade_type = (row["trade_type"] or "").lower()
        if "purchase" in trade_type or "buy" in trade_type:
            holdings[ticker]["buys"] += 1
        elif "sale" in trade_type or "sell" in trade_type:
            holdings[ticker]["sells"] += 1

    # Convert to list sorted by last trade date
    result = sorted(holdings.values(), key=lambda h: h["last_trade_date"] or "", reverse=True)
    return result
