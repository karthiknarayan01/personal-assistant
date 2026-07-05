import json

from .. import db

# Well-known keys the agent should ask about once and then reuse:
#   full_name, first_name, last_name, email, phone, location,
#   linkedin_url, visa_sponsorship_required, work_authorization,
#   veteran_status, disability_status, gender_identity, race_ethnicity,
#   target_roles (JSON list), roles_per_run (int),
#   candidate_summary (JSON: companies, skills, education, achievements)
# Any other key the agent discovers it needs repeatedly can be stored the
# same way — this store is intentionally schema-less beyond key/value.


def get_profile() -> dict:
    """Reads all saved candidate profile fields and preferences.

    Always check this before asking the user something — if a field like
    visa sponsorship status or target roles is already here, reuse it
    instead of asking again.

    Returns:
        dict: {"status": "success", "fields": {key: value, ...}}. Values
        that were saved as JSON (e.g. target_roles, candidate_summary) are
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
    """Saves or updates one or more candidate profile fields.

    Use this right after the user answers a question you don't already
    have stored (name, visa sponsorship, target roles, how many roles to
    apply this run, etc.) so they're never asked again. List/dict values
    are stored as JSON automatically.

    Args:
        fields: Mapping of field name to value, e.g.
            {"visa_sponsorship_required": "no", "roles_per_run": 5}.

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
