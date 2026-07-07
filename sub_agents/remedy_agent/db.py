import datetime
import os
import sqlite3
import threading

_DB_PATH = os.environ.get(
    "REMEDY_AGENT_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "remedy_agent.db"),
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
            CREATE TABLE IF NOT EXISTS remedies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ailment TEXT NOT NULL,
                tradition TEXT NOT NULL,
                remedy_name TEXT NOT NULL,
                description TEXT NOT NULL,
                cautions TEXT NOT NULL,
                source TEXT NOT NULL,
                added_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_remedies_ailment ON remedies (ailment)"
        )


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    return _connect()


def lock() -> threading.Lock:
    return _lock
