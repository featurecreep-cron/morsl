"""Menu repository — generated menus per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from morsl.db import json_col, parse_json_col


class MenuRepository:
    """Per-user menu storage backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_current(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Return the current menu for a user, or None."""
        row = self._conn.execute(
            "SELECT id, profile_name, recipes, generated_at, metadata "
            "FROM menus WHERE user_id = ? AND is_current = 1 "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def save_current(
        self,
        user_id: int,
        profile_name: str,
        recipes: List[Dict],
        generated_at: str,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Save a new current menu, marking previous current as non-current."""
        self._conn.execute(
            "UPDATE menus SET is_current = 0 WHERE user_id = ? AND is_current = 1",
            (user_id,),
        )
        cur = self._conn.execute(
            "INSERT INTO menus (user_id, profile_name, recipes, generated_at, "
            "metadata, is_current) VALUES (?, ?, ?, ?, ?, 1)",
            (
                user_id,
                profile_name,
                json_col(recipes),
                generated_at,
                json_col(metadata) if metadata else None,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_recipes(self, menu_id: int, recipes: List[Dict]) -> None:
        """Update the recipes on an existing menu (used by swap)."""
        self._conn.execute(
            "UPDATE menus SET recipes = ? WHERE id = ?",
            (json_col(recipes), menu_id),
        )
        self._conn.commit()

    def clear_current(self, user_id: int) -> None:
        """Mark all menus for a user as non-current."""
        self._conn.execute(
            "UPDATE menus SET is_current = 0 WHERE user_id = ? AND is_current = 1",
            (user_id,),
        )
        self._conn.commit()

    def list_recent(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent menus for a user, newest first."""
        rows = self._conn.execute(
            "SELECT id, profile_name, recipes, generated_at, metadata "
            "FROM menus WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "profile_name": row["profile_name"],
            "recipes": parse_json_col(row["recipes"], []),
            "generated_at": row["generated_at"],
            "metadata": parse_json_col(row["metadata"]),
        }
