"""Profile repository — constraint-based menu generation profiles per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from morsl.db import json_col, parse_json_col


class ProfileRepository:
    """Per-user profile CRUD backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self, user_id: int) -> List[Dict[str, Any]]:
        """Return all profiles for a user with parsed config."""
        rows = self._conn.execute(
            "SELECT id, name, config, is_default, created_at, updated_at "
            "FROM profiles WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "config": parse_json_col(row["config"], {}),
                "is_default": bool(row["is_default"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def get_by_name(self, user_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Return a single profile by name, or None."""
        row = self._conn.execute(
            "SELECT id, name, config, is_default, created_at, updated_at "
            "FROM profiles WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "config": parse_json_col(row["config"], {}),
            "is_default": bool(row["is_default"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create(
        self, user_id: int, name: str, config: Dict[str, Any], is_default: bool = False
    ) -> int:
        """Insert a new profile. Returns the new row ID."""
        cur = self._conn.execute(
            "INSERT INTO profiles (user_id, name, config, is_default) VALUES (?, ?, ?, ?)",
            (user_id, name, json_col(config), int(is_default)),
        )
        self._conn.commit()
        return cur.lastrowid

    def update(self, user_id: int, name: str, config: Dict[str, Any]) -> None:
        """Update an existing profile's config."""
        self._conn.execute(
            "UPDATE profiles SET config = ?, updated_at = datetime('now') "
            "WHERE user_id = ? AND name = ?",
            (json_col(config), user_id, name),
        )
        self._conn.commit()

    def delete(self, user_id: int, name: str) -> bool:
        """Delete a profile. Returns True if a row was deleted."""
        cur = self._conn.execute(
            "DELETE FROM profiles WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def set_default(self, user_id: int, name: str) -> None:
        """Mark one profile as default, clearing the flag from all others."""
        self._conn.execute("UPDATE profiles SET is_default = 0 WHERE user_id = ?", (user_id,))
        self._conn.execute(
            "UPDATE profiles SET is_default = 1 WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        self._conn.commit()

    def clear_default(self, user_id: int, name: str) -> None:
        """Remove the default flag from a single profile."""
        self._conn.execute(
            "UPDATE profiles SET is_default = 0 WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        self._conn.commit()

    def exists(self, user_id: int, name: str) -> bool:
        """Check if a profile exists."""
        row = self._conn.execute(
            "SELECT 1 FROM profiles WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        return row is not None
