"""Settings repository — key-value pairs per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict

from morsl.db import json_col, parse_json_col


class SettingsRepository:
    """Per-user settings stored as key-value rows."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_all(self, user_id: int) -> Dict[str, Any]:
        """Return all settings for a user as a dict."""
        rows = self._conn.execute(
            "SELECT key, value FROM settings WHERE user_id = ?", (user_id,)
        ).fetchall()
        return {row["key"]: parse_json_col(row["value"]) for row in rows}

    def get(self, user_id: int, key: str, default: Any = None) -> Any:
        """Return a single setting value, or default if not set."""
        row = self._conn.execute(
            "SELECT value FROM settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
        if row is None:
            return default
        return parse_json_col(row["value"], default)

    def set(self, user_id: int, key: str, value: Any) -> None:
        """Set a single setting (upsert)."""
        self._conn.execute(
            "INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
            (user_id, key, json_col(value)),
        )
        self._conn.commit()

    def set_many(self, user_id: int, updates: Dict[str, Any]) -> None:
        """Set multiple settings at once."""
        for key, value in updates.items():
            self._conn.execute(
                "INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
                (user_id, key, json_col(value)),
            )
        self._conn.commit()

    def delete(self, user_id: int, key: str) -> None:
        """Remove a single setting."""
        self._conn.execute("DELETE FROM settings WHERE user_id = ? AND key = ?", (user_id, key))
        self._conn.commit()

    def delete_all(self, user_id: int) -> None:
        """Remove all settings for a user."""
        self._conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
        self._conn.commit()
