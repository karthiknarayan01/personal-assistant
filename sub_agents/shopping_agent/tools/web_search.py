"""General web search, via DuckDuckGo's HTML search (no API key, no cost)."""

import logging

from ddgs import DDGS

_logger = logging.getLogger(__name__)


def web_search(query: str, limit: int = 5) -> dict:
    """Searches the web for a query.

    Use for reviews, ratings, and price/retailer context that
    search_slickdeals didn't surface — never invent a product, price, or
    rating you didn't actually find via a tool.

    Args:
        query: Search term, e.g. "best rated men's chinos 2026".
        limit: Maximum number of results to return.

    Returns:
        dict: {"status": "success", "results": [{"title", "url",
        "snippet"}, ...]} or {"status": "error", "error_message": "..."}.
    """
    try:
        hits = DDGS().text(query, max_results=limit)
    except Exception:
        _logger.exception("Web search failed for query %r", query)
        return {
            "status": "error",
            "error_message": "Could not reach web search right now.",
        }

    results = [
        {
            "title": hit.get("title", ""),
            "url": hit.get("href", ""),
            "snippet": hit.get("body", ""),
        }
        for hit in hits
    ]
    return {"status": "success", "results": results}
