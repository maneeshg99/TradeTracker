from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
import html

import config


def _escape(text):
    if text is None:
        return ""
    return html.escape(str(text))


def _format_rfc822(date_str):
    """Try to parse common date formats and return RFC 822."""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except (ValueError, TypeError):
            continue
    return None


def generate_feed(trades):
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = config.FEED_TITLE
    SubElement(channel, "description").text = config.FEED_DESCRIPTION
    SubElement(channel, "link").text = f"http://localhost:{config.PORT}/feed"
    SubElement(channel, "language").text = "en"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    for t in trades:
        item = SubElement(channel, "item")

        ticker_display = t.get("ticker") or "N/A"
        title = f"{t['politician']} - {t['trade_type']} {ticker_display}"
        if t.get("amount"):
            title += f" ({t['amount']})"
        SubElement(item, "title").text = title

        # Build description
        lines = []
        lines.append(f"Politician: {t['politician']} ({t['chamber']})")
        if t.get("district"):
            lines.append(f"District: {t['district']}")
        lines.append(f"Trade: {t['trade_type']}")
        if t.get("ticker"):
            lines.append(f"Ticker: {t['ticker']}")
        if t.get("asset_description"):
            lines.append(f"Asset: {t['asset_description']}")
        if t.get("amount"):
            lines.append(f"Amount: {t['amount']}")
        if t.get("owner"):
            lines.append(f"Owner: {t['owner']}")
        if t.get("transaction_date"):
            lines.append(f"Transaction Date: {t['transaction_date']}")
        if t.get("disclosure_date"):
            lines.append(f"Disclosure Date: {t['disclosure_date']}")
        SubElement(item, "description").text = "\n".join(lines)

        if t.get("ptr_link"):
            SubElement(item, "link").text = t["ptr_link"]
            SubElement(item, "guid").text = t["ptr_link"]
        else:
            SubElement(item, "guid").text = t["id"]

        if t.get("disclosure_date"):
            rfc_date = _format_rfc822(t["disclosure_date"])
            if rfc_date:
                SubElement(item, "pubDate").text = rfc_date

    raw_xml = tostring(rss, encoding="unicode", xml_declaration=False)
    pretty = parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw_xml}').toprettyxml(indent="  ")
    # Remove extra xml declaration from toprettyxml
    lines = pretty.split("\n")
    return "\n".join(lines).encode("utf-8")
