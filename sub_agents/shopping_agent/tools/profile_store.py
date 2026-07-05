import json

from .. import db

# Keys are namespaced by convention so this stays flexible across clothing
# categories, e.g.:
#   "measurements:pants" -> {"waist": 32, "inseam": 32, "size": "32x32"}
#   "measurements:shirt" -> {"size": "M", "chest": 40}
#   "measurements:shoe"  -> {"size": "10 US"}
#   "preferred_brands:pants" -> ["Levi's", "Uniqlo"]
#   "notes:pants" -> "prefers slim fit, avoids stiff denim"
#   "quality_vs_cost_priority" -> "quality" (general preference, no category)


def get_profile() -> dict:
    """Reads all saved measurements, brand preferences, and shopping notes.

    Always check this before asking the user for a size/measurement or
    brand preference for a category — if it's already here, reuse it
    instead of asking again.

    Returns:
        dict: {"status": "success", "fields": {key: value, ...}}. Values
        saved as JSON (measurements dicts, brand-preference lists) are
        returned already parsed.
    """
    db.init_db()
    with db.lock(), db.connect() as conn:
        rows = conn.execute("SELECT key, value FROM profile_fields").fetchall()

    fields = {}
    for row in rows:
        try:
            fields[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            fields[row["key"]] = row["value"]

    return {"status": "success", "fields": fields}


def save_profile_fields(fields: dict) -> dict:
    """Saves or updates measurements, brand preferences, or notes.

    Use this right after the user gives a size/measurement or brand
    preference you don't already have stored, following the key
    convention "measurements:<category>", "preferred_brands:<category>",
    "notes:<category>" — so it's never asked again. Also call this
    whenever record_purchase reveals a size or brand that wasn't already
    on file, so future searches in that category skip the question.

    Args:
        fields: Mapping of field name to value, e.g.
            {"measurements:pants": {"waist": 32, "inseam": 32},
             "preferred_brands:pants": ["Levi's", "Uniqlo"]}.

    Returns:
        dict: {"status": "success", "saved_keys": [...]}.
    """
    db.init_db()
    saved = []
    with db.lock(), db.connect() as conn:
        for key, value in fields.items():
            stored_value = json.dumps(value) if not isinstance(value, str) else value
            conn.execute(
                "INSERT INTO profile_fields (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, stored_value, db.now_iso()),
            )
            saved.append(key)

    return {"status": "success", "saved_keys": saved}
