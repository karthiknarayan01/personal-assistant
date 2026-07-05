import datetime
import os
import sqlite3
import threading

_DB_PATH = os.environ.get(
    "SHOPPING_AGENT_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "shopping_agent.db"),
)

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                brand TEXT,
                size_or_measurements TEXT,
                color TEXT,
                price REAL,
                currency TEXT DEFAULT 'USD',
                rating REAL,
                source_url TEXT,
                deal_source TEXT,
                purchased_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_purchases_category ON purchases (category)"
        )
        # Flexible key/value store for measurements, preferred brands, style
        # notes, etc. Keys are namespaced by convention, e.g.
        # "measurements:pants", "preferred_brands:pants", "notes:general".
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_fields (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    return _connect()


def lock() -> threading.Lock:
    return _lock
