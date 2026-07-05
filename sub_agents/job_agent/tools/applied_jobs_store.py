import datetime

from .. import db

_COOLDOWN_DAYS = 90


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def check_cooldown(company: str, role_title: str) -> dict:
    """Checks whether a role at a company was already applied to recently.

    Use this before preparing any application. A role is on cooldown if an
    application to the same company for the same (or a near-identical)
    role title was recorded within the last 90 days — that role must not
    be applied to again until the cooldown expires.

    Args:
        company: Company name as it appears on the job posting.
        role_title: Role title as it appears on the job posting.

    Returns:
        dict: {"status": "success", "on_cooldown": bool,
        "last_applied_at": "<ISO8601>" or None,
        "days_remaining": int or 0}.
    """
    db.init_db()
    company_n = _normalize(company)
    role_n = _normalize(role_title)

    with db.lock(), db.connect() as conn:
        rows = conn.execute(
            "SELECT applied_at FROM applications "
            "WHERE lower(trim(company)) = ? AND lower(trim(role_title)) = ? "
            "ORDER BY applied_at DESC LIMIT 1",
            (company_n, role_n),
        ).fetchall()

    if not rows:
        return {"status": "success", "on_cooldown": False, "last_applied_at": None, "days_remaining": 0}

    last_applied_at = rows[0]["applied_at"]
    last_dt = datetime.datetime.fromisoformat(last_applied_at)
    elapsed = datetime.datetime.now(datetime.timezone.utc) - last_dt
    remaining = _COOLDOWN_DAYS - elapsed.days

    if remaining <= 0:
        return {
            "status": "success",
            "on_cooldown": False,
            "last_applied_at": last_applied_at,
            "days_remaining": 0,
        }

    return {
        "status": "success",
        "on_cooldown": True,
        "last_applied_at": last_applied_at,
        "days_remaining": remaining,
    }


def record_application(
    source: str,
    company: str,
    role_title: str,
    job_url: str = "",
    external_job_id: str = "",
) -> dict:
    """Records a submitted application so it isn't applied to again for 90 days.

    Call this immediately after a real submission succeeds — never before,
    and never for a draft that hasn't actually been submitted.

    Args:
        source: One of "handshake", "linkedin", "jobright".
        company: Company name as it appears on the job posting.
        role_title: Role title as it appears on the job posting.
        job_url: The job posting URL, if available.
        external_job_id: The job board's own ID for the posting, if available.

    Returns:
        dict: {"status": "success", "id": <row id>} or
        {"status": "error", "error_message": "..."}.
    """
    db.init_db()
    try:
        with db.lock(), db.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO applications "
                "(source, company, role_title, job_url, external_job_id, applied_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'submitted')",
                (source, company, role_title, job_url, external_job_id, db.now_iso()),
            )
            return {"status": "success", "id": cursor.lastrowid}
    except Exception:
        return {
            "status": "error",
            "error_message": "Could not record the application locally.",
        }


def list_recent_applications(days: int = 90) -> dict:
    """Lists applications submitted within the given number of days.

    Args:
        days: How many days back to look. Defaults to 90 (the cooldown
            window).

    Returns:
        dict: {"status": "success", "applications": [{"source", "company",
        "role_title", "job_url", "applied_at"}, ...]}.
    """
    db.init_db()
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    ).isoformat()

    with db.lock(), db.connect() as conn:
        rows = conn.execute(
            "SELECT source, company, role_title, job_url, applied_at FROM applications "
            "WHERE applied_at >= ? ORDER BY applied_at DESC",
            (cutoff,),
        ).fetchall()

    return {"status": "success", "applications": [dict(r) for r in rows]}
