"""Weekly plan repository — generated weekly plans per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from morsl.db import json_col, parse_json_col


class WeeklyPlanRepository:
    """Per-user weekly plan storage backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, user_id: int, template_name: str) -> Optional[Dict[str, Any]]:
        """Return the plan for a template, or None."""
        row = self._conn.execute(
            "SELECT id, template_name, plan_data, week_start, generated_at "
            "FROM weekly_plans WHERE user_id = ? AND template_name = ?",
            (user_id, template_name),
        ).fetchone()
        if row is None:
            return None
        return parse_json_col(row["plan_data"])

    def save(
        self, user_id: int, template_name: str, plan_data: Dict[str, Any], week_start: str
    ) -> None:
        """Save or replace a weekly plan for a template."""
        self._conn.execute(
            "INSERT INTO weekly_plans (user_id, template_name, plan_data, week_start) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, template_name) DO UPDATE SET "
            "plan_data = excluded.plan_data, week_start = excluded.week_start, "
            "generated_at = datetime('now')",
            (user_id, template_name, json_col(plan_data), week_start),
        )
        self._conn.commit()

    def delete(self, user_id: int, template_name: str) -> bool:
        """Delete a weekly plan. Returns True if a row was deleted."""
        cur = self._conn.execute(
            "DELETE FROM weekly_plans WHERE user_id = ? AND template_name = ?",
            (user_id, template_name),
        )
        self._conn.commit()
        return cur.rowcount > 0
