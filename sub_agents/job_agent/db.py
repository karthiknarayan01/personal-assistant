import datetime
import os
import sqlite3
import threading

_DB_PATH = os.environ.get(
    "JOB_AGENT_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "job_agent.db"),
)

_lock = threading.Lock()

# Overridable in case this db file ever ends up on a filesystem that
# doesn't support WAL's locking requirements (e.g. a network mount).
_JOURNAL_MODE = os.environ.get("SQLITE_JOURNAL_MODE", "WAL")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA journal_mode={_JOURNAL_MODE}")
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                company TEXT NOT NULL,
                role_title TEXT NOT NULL,
                job_url TEXT,
                external_job_id TEXT,
                applied_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'submitted'
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_applications_company_role
            ON applications (company, role_title)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_fields (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_drafts (
                job_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                company TEXT NOT NULL,
                role_title TEXT NOT NULL,
                job_url TEXT,
                draft_summary TEXT NOT NULL,
                screenshot_path TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    return _connect()


def lock() -> threading.Lock:
    return _lock
