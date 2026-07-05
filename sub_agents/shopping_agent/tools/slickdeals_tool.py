"""Slickdeals deal search, via their documented public RSS search feed
(https://help.slickdeals.net/hc/en-us/articles/115004693773-How-to-Use-RSS-feeds)
— no scraping, no account/auth needed, first-party and publicly
documented.
"""

import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)
_RSS_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
_THUMB_SCORE_RE = re.compile(r"Thumb Score:\s*([+-]?\d+)")


def search_slickdeals(query: str, limit: int = 10) -> dict:
    """Searches Slickdeals for deals matching a query.

    Always check this when deal-hunting, alongside google_search for
    reviews/ratings/price context — never invent or guess deals.

    Args:
        query: Search term, e.g. "men's chinos" or "running shoes".
        limit: Maximum number of deals to return, ranked by community
            "thumb score" (Slickdeals' popularity/quality signal).

    Returns:
        dict: {"status": "success", "deals": [{"title", "url",
        "description", "thumb_score"}, ...]} or {"status": "error",
        "error_message": "..."}.
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

        deals.append(
            {
                "title": title,
                "url": link,
                "description": description,
                "thumb_score": thumb_score,
            }
        )

    deals.sort(key=lambda d: d["thumb_score"], reverse=True)
    return {"status": "success", "deals": deals[:limit]}
