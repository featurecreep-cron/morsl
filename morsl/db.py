"""SQLite database layer for morsl.

WAL mode, stdlib sqlite3, hand-rolled migrations. No ORM.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Current schema version — increment when adding migrations
SCHEMA_VERSION = 2

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    config TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    profile_name TEXT NOT NULL,
    recipes TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    metadata TEXT,
    is_current INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    config TEXT NOT NULL,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    recipe_id INTEGER NOT NULL,
    recipe_name TEXT NOT NULL,
    customer_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'received',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generation_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    profile_name TEXT NOT NULL,
    recipe_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'unknown',
    metadata TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_settings_user ON settings(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_menus_user_current ON menus(user_id, is_current);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_history_user ON generation_history(user_id, generated_at);
"""

_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS weekly_plans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    template_name TEXT NOT NULL,
    plan_data TEXT NOT NULL,
    week_start TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, template_name)
);

CREATE INDEX IF NOT EXISTS idx_weekly_plans_user ON weekly_plans(user_id, template_name);
"""

# Migrations keyed by version number. Each is a list of SQL statements.
_MIGRATIONS: dict[int, tuple[str, list[str]]] = {
    1: ("Initial schema", [_SCHEMA_V1]),
    2: ("Weekly plans table", [_SCHEMA_V2]),
}


def _get_db_path(data_dir: str) -> str:
    return os.path.join(data_dir, "morsl.db")


def get_connection(data_dir: str = "data") -> sqlite3.Connection:
    """Open a connection to the morsl database.

    Creates the database and runs migrations if needed. WAL mode enabled.
    """
    os.makedirs(data_dir, exist_ok=True)
    db_path = _get_db_path(data_dir)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _run_migrations(conn)
    return conn


def _current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version, or 0 if no schema exists."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations."""
    current = _current_version(conn)
    if current >= SCHEMA_VERSION:
        return

    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version not in _MIGRATIONS:
            raise RuntimeError(f"Missing migration for version {version}")
        description, statements = _MIGRATIONS[version]
        logger.info("Applying migration v%d: %s", version, description)
        for sql in statements:
            conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (version, description),
        )
        conn.commit()

    logger.info("Database at schema version %d", SCHEMA_VERSION)


# ---------------------------------------------------------------------------
# Connection pool (single shared connection with WAL — safe for concurrent reads)
# ---------------------------------------------------------------------------

_pool_lock = threading.Lock()
_pool: dict[str, sqlite3.Connection] = {}


def get_db(data_dir: str = "data") -> sqlite3.Connection:
    """Get or create a shared database connection for the given data_dir.

    WAL mode allows concurrent readers with a single writer. For morsl's
    workload (low write volume, moderate read volume) a single shared
    connection is sufficient.
    """
    with _pool_lock:
        if data_dir not in _pool:
            _pool[data_dir] = get_connection(data_dir)
        return _pool[data_dir]


def ensure_default_user(conn: sqlite3.Connection, user_id: int = 1) -> None:
    """Ensure the default user row exists (for pre-auth single-user mode)."""
    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, 'default', '')",
        (user_id,),
    )
    conn.commit()


def close_all() -> None:
    """Close all pooled connections. Call on shutdown."""
    with _pool_lock:
        for conn in _pool.values():
            conn.close()
        _pool.clear()


# ---------------------------------------------------------------------------
# JSON helpers for columns that store JSON blobs
# ---------------------------------------------------------------------------


def json_col(value: Any) -> str:
    """Serialize a Python object for storage in a TEXT column."""
    return json.dumps(value, separators=(",", ":"))


def parse_json_col(raw: str | None, default: Any = None) -> Any:
    """Deserialize a JSON TEXT column. Returns default on None or error."""
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
