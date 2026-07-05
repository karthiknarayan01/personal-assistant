from .. import db


def record_purchase(
    category: str,
    item_name: str,
    brand: str = "",
    size_or_measurements: str = "",
    color: str = "",
    price: float = 0.0,
    currency: str = "USD",
    rating: float = 0.0,
    source_url: str = "",
    deal_source: str = "",
) -> dict:
    """Records a purchase the user made, to learn preferences over time.

    Call this whenever the user says they bought something. If
    size_or_measurements or brand is new information for this category,
    also call save_profile_fields (profile_store) with
    "measurements:<category>" / "preferred_brands:<category>" so it's
    never asked again.

    Args:
        category: Clothing category, e.g. "pants", "shirt", "shoes".
        item_name: Product name as purchased.
        brand: Brand name.
        size_or_measurements: Size or measurements as purchased, e.g.
            "32x32" or "M".
        color: Color purchased.
        price: Price paid.
        currency: Currency code, default "USD".
        rating: The product's rating at time of purchase (e.g. out of 5),
            if known.
        source_url: Product or deal page URL.
        deal_source: Where the deal was found, e.g. "slickdeals",
            "google_search", "amazon".

    Returns:
        dict: {"status": "success", "id": <row id>} or
        {"status": "error", "error_message": "..."}.
    """
    db.init_db()
    try:
        with db.lock(), db.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO purchases "
                "(category, item_name, brand, size_or_measurements, color, price, "
                "currency, rating, source_url, deal_source, purchased_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    category,
                    item_name,
                    brand,
                    size_or_measurements,
                    color,
                    price,
                    currency,
                    rating,
                    source_url,
                    deal_source,
                    db.now_iso(),
                ),
            )
            return {"status": "success", "id": cursor.lastrowid}
    except Exception:
        return {
            "status": "error",
            "error_message": "Could not record that purchase locally.",
        }


def get_purchase_history(category: str = "", limit: int = 20) -> dict:
    """Lists past purchases, optionally filtered to one category.

    Check this before searching, to see prior brands/sizes/price points
    for the category and avoid re-asking or re-recommending something
    just bought.

    Args:
        category: Clothing category to filter to, e.g. "pants". Empty
            string returns all categories.
        limit: Maximum number of rows to return, most recent first.

    Returns:
        dict: {"status": "success", "purchases": [{"category",
        "item_name", "brand", "size_or_measurements", "color", "price",
        "currency", "rating", "source_url", "deal_source",
        "purchased_at"}, ...]}.
    """
    db.init_db()
    with db.lock(), db.connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM purchases WHERE category = ? "
                "ORDER BY purchased_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM purchases ORDER BY purchased_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return {"status": "success", "purchases": [dict(r) for r in rows]}


def get_brand_affinity(category: str = "") -> dict:
    """Summarizes which brands the user buys most often and rates highest.

    Use this as a quick signal for brand preference in a category before
    asking the user, especially when profile_store has no explicit
    "preferred_brands:<category>" entry yet.

    Args:
        category: Clothing category to filter to. Empty string covers
            all categories.

    Returns:
        dict: {"status": "success", "brands": [{"brand", "purchase_count",
        "average_rating"}, ...]}, ordered by purchase count then rating.
    """
    db.init_db()
    with db.lock(), db.connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT brand, COUNT(*) as purchase_count, AVG(rating) as average_rating "
                "FROM purchases WHERE category = ? AND brand != '' "
                "GROUP BY brand ORDER BY purchase_count DESC, average_rating DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT brand, COUNT(*) as purchase_count, AVG(rating) as average_rating "
                "FROM purchases WHERE brand != '' "
                "GROUP BY brand ORDER BY purchase_count DESC, average_rating DESC"
            ).fetchall()

    return {"status": "success", "brands": [dict(r) for r in rows]}
