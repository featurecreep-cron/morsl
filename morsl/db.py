"""SQLite database layer for morsl.

WAL mode, stdlib sqlite3, hand-rolled migrations. No ORM.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
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


# Snapshots live in <data_dir>/backups/. Daily ones keep a week; pre-migration
# ones are rarer and only need to outlive the upgrade that made them.
BACKUP_DIR_NAME = "backups"
DAILY_BACKUPS_KEPT = 7
MIGRATION_BACKUPS_KEPT = 3


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

    # A migration is the likeliest moment to lose data, and an upgrade can land
    # nearly a day after the last daily snapshot. A brand-new database has
    # nothing to lose. If the snapshot fails the migration does not run: the
    # error propagates rather than migrating without a way back.
    if current > 0:
        db_file = _main_db_file(conn)
        if db_file:
            backup_database(db_file, f"pre-v{SCHEMA_VERSION}", keep=MIGRATION_BACKUPS_KEPT)

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
# Backups
# ---------------------------------------------------------------------------


def _main_db_file(conn: sqlite3.Connection) -> str:
    """Path of the connection's main database file; empty for in-memory."""
    for row in conn.execute("PRAGMA database_list").fetchall():
        if row[1] == "main":
            return row[2] or ""
    return ""


def _backups_for(backup_dir: str, reason: str) -> list[str]:
    """Existing snapshots for one reason, oldest first (the timestamp sorts)."""
    suffix = f"-{reason}.db"
    try:
        names = os.listdir(backup_dir)
    except FileNotFoundError:
        return []
    return sorted(n for n in names if n.startswith("morsl-") and n.endswith(suffix))


def backup_database(db_file: str, reason: str = "daily", keep: int = DAILY_BACKUPS_KEPT) -> str:
    """Snapshot db_file into a timestamped file and prune older ones of the same reason.

    Uses SQLite's online backup API from a separate connection, so the result is
    consistent even with WAL frames not yet checkpointed and the app still
    writing. The snapshot is written under a temporary name and renamed into
    place, so an interrupted backup never counts as one.

    Returns the path of the new snapshot.
    """
    # sqlite3.connect would create an empty database and back that up instead.
    if not os.path.exists(db_file):
        raise FileNotFoundError(db_file)
    backup_dir = os.path.join(os.path.dirname(db_file), BACKUP_DIR_NAME)
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = os.path.join(backup_dir, f"morsl-{stamp}-{reason}.db")
    partial = final + ".partial"

    try:
        src = sqlite3.connect(db_file)
        try:
            dest = sqlite3.connect(partial)
            try:
                src.backup(dest)
            finally:
                dest.close()
        finally:
            src.close()
        os.replace(partial, final)
    except (OSError, sqlite3.Error):
        with contextlib.suppress(FileNotFoundError):
            os.remove(partial)
        raise
    logger.info("Database backed up to %s", final)

    for old in _backups_for(backup_dir, reason)[:-keep]:
        os.remove(os.path.join(backup_dir, old))
        logger.info("Pruned old backup %s", old)
    return final


def latest_backup_time(data_dir: str, reason: str = "daily") -> datetime | None:
    """When the newest snapshot for reason was taken, or None if there is none."""
    existing = _backups_for(os.path.join(data_dir, BACKUP_DIR_NAME), reason)
    if not existing:
        return None
    stamp = existing[-1].removeprefix("morsl-").split("-", 1)[0]
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def backup_if_stale(data_dir: str, max_age: timedelta = timedelta(days=1)) -> str | None:
    """Take a daily snapshot unless one younger than max_age exists.

    Called at startup, so a container that is never up at the scheduled hour
    still gets its backups. Returns the new snapshot's path, or None if skipped.
    """
    db_file = _get_db_path(data_dir)
    if not os.path.exists(db_file):
        return None
    last = latest_backup_time(data_dir)
    if last is not None and datetime.now(timezone.utc) - last < max_age:
        return None
    return backup_database(db_file)


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
