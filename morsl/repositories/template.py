"""Template repository — weekly meal-plan templates per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from morsl.db import json_col, parse_json_col


class TemplateRepository:
    """Per-user template CRUD backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self, user_id: int) -> List[Dict[str, Any]]:
        """Return all templates for a user."""
        rows = self._conn.execute(
            "SELECT id, name, config FROM templates WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "config": parse_json_col(row["config"], {}),
            }
            for row in rows
        ]

    def get_by_name(self, user_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Return a single template by name, or None."""
        row = self._conn.execute(
            "SELECT id, name, config FROM templates WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "config": parse_json_col(row["config"], {}),
        }

    def create(self, user_id: int, name: str, config: Dict[str, Any]) -> int:
        """Insert a new template. Returns the new row ID."""
        cur = self._conn.execute(
            "INSERT INTO templates (user_id, name, config) VALUES (?, ?, ?)",
            (user_id, name, json_col(config)),
        )
        self._conn.commit()
        return cur.lastrowid

    def update(self, user_id: int, name: str, config: Dict[str, Any]) -> None:
        """Update an existing template's config."""
        self._conn.execute(
            "UPDATE templates SET config = ? WHERE user_id = ? AND name = ?",
            (json_col(config), user_id, name),
        )
        self._conn.commit()

    def delete(self, user_id: int, name: str) -> bool:
        """Delete a template. Returns True if a row was deleted."""
        cur = self._conn.execute(
            "DELETE FROM templates WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def exists(self, user_id: int, name: str) -> bool:
        """Check if a template exists."""
        row = self._conn.execute(
            "SELECT 1 FROM templates WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        return row is not None
