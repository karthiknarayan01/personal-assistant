"""Slickdeals deal search, via their documented public RSS search feed
(https://help.slickdeals.net/hc/en-us/articles/115004693773-How-to-Use-RSS-feeds)
— no scraping, no account/auth needed, first-party and publicly
documented.
"""

import html
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)
_RSS_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
_THUMB_SCORE_RE = re.compile(r"Thumb Score:\s*([+-]?\d+)")
_IMG_RE = re.compile(r'<img[^>]+src="(https://[^"]+)"', re.IGNORECASE)
_CLICK_LINK_RE = re.compile(
    r'<a[^>]+href="(https://slickdeals\.net/click\?[^"]+)"', re.IGNORECASE
)
_PRICE_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_DISCOUNT_RE = re.compile(r"(\d{1,3})%\s*off", re.IGNORECASE)
_FREE_SHIP_RE = re.compile(r"free\s+shipping", re.IGNORECASE)
_RETAILER_RE = re.compile(r"\[([\w.-]+\.\w{2,})\]")


def _extract_deal_extras(content_encoded: str, title: str, description: str) -> dict:
    """Best-effort extraction of extra deal fields from RSS text.

    Never guesses — a field is None/False if its pattern isn't found,
    since these values feed model-facing output that must not show
    fabricated data.
    """
    image_match = _IMG_RE.search(content_encoded)
    click_match = _CLICK_LINK_RE.search(content_encoded)
    text = f"{title} {description}"
    price_match = _PRICE_RE.search(text)
    discount_match = _DISCOUNT_RE.search(text)
    retailer_match = _RETAILER_RE.search(text)

    return {
        "image_url": html.unescape(image_match.group(1)) if image_match else None,
        "click_url": html.unescape(click_match.group(1)) if click_match else None,
        "price": price_match.group(0) if price_match else None,
        "discount_percent": (
            int(discount_match.group(1)) if discount_match else None
        ),
        "free_shipping": bool(_FREE_SHIP_RE.search(text)),
        "retailer": retailer_match.group(1) if retailer_match else None,
    }


def search_slickdeals(query: str, limit: int = 10) -> dict:
    """Searches Slickdeals for deals matching a query.

    Always check this when deal-hunting, alongside web_search for
    reviews/ratings/price context — never invent or guess deals.

    Args:
        query: Search term, e.g. "men's chinos" or "running shoes".
        limit: Maximum number of deals to return, ranked by community
            "thumb score" (Slickdeals' popularity/quality signal).

    Returns:
        dict: {"status": "success", "deals": [{"title", "url", "buy_url",
        "image_url", "description", "price", "retailer",
        "discount_percent", "free_shipping", "thumb_score"}, ...]} or
        {"status": "error", "error_message": "..."}. "buy_url" is a
        direct Slickdeals click-tracking redirect straight to the
        retailer when the feed has one, else it falls back to the
        discussion page ("url"). Fields not found in the feed are
        None/False — never guessed. When writing a deal card, OMIT any
        field that's None/False entirely rather than writing a
        placeholder like "N/A" or "$X.XX".
    """
    url = "https://slickdeals.net/newsearch.php?" + urllib.parse.urlencode(
        {"q": query, "rss": "1"}
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
        root = ET.fromstring(raw)
    except Exception:
        _logger.exception("Slickdeals search failed for query %r", query)
        return {
            "status": "error",
            "error_message": "Could not reach Slickdeals right now.",
        }

    deals = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = " ".join((item.findtext("description") or "").split())
        content_encoded = item.findtext("content:encoded", namespaces=_RSS_NS) or ""
        match = _THUMB_SCORE_RE.search(content_encoded)
        thumb_score = int(match.group(1)) if match else 0
        extras = _extract_deal_extras(content_encoded, title, description)

        deals.append(
            {
                "title": title,
                "url": link,
                "buy_url": extras["click_url"] or link,
                "image_url": extras["image_url"],
                "description": description,
                "price": extras["price"],
                "retailer": extras["retailer"],
                "discount_percent": extras["discount_percent"],
                "free_shipping": extras["free_shipping"],
                "thumb_score": thumb_score,
            }
        )

    deals.sort(key=lambda d: d["thumb_score"], reverse=True)
    return {"status": "success", "deals": deals[:limit]}
