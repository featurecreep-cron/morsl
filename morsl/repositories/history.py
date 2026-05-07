"""History repository — generation history per user."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from morsl.db import json_col, parse_json_col


class HistoryRepository:
    """Per-user generation history backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_entry(
        self,
        user_id: int,
        profile_name: str,
        recipe_count: int,
        duration_ms: int,
        status: str,
        generated_at: str,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Insert a new history entry. Returns the new row ID."""
        cur = self._conn.execute(
            "INSERT INTO generation_history "
            "(user_id, profile_name, recipe_count, duration_ms, status, "
            "generated_at, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                profile_name,
                recipe_count,
                duration_ms,
                status,
                generated_at,
                json_col(metadata) if metadata else None,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_entries(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return paginated entries (newest first) and total count."""
        total_row = self._conn.execute(
            "SELECT COUNT(*) FROM generation_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total = total_row[0]

        rows = self._conn.execute(
            "SELECT id, profile_name, recipe_count, duration_ms, status, "
            "generated_at, metadata FROM generation_history "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        entries = [self._row_to_dict(row) for row in rows]
        return entries, total

    def get_entry(self, user_id: int, entry_id: int) -> Optional[Dict[str, Any]]:
        """Get a single history entry by ID."""
        row = self._conn.execute(
            "SELECT id, profile_name, recipe_count, duration_ms, status, "
            "generated_at, metadata FROM generation_history "
            "WHERE user_id = ? AND id = ?",
            (user_id, entry_id),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_analytics(self, user_id: int) -> Dict[str, Any]:
        """Compute generation analytics from stored history."""
        rows = self._conn.execute(
            "SELECT profile_name, recipe_count, duration_ms, status, metadata "
            "FROM generation_history WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 100",
            (user_id,),
        ).fetchall()

        total = len(rows)
        if total == 0:
            return {
                "total_generations": 0,
                "avg_duration_ms": 0,
                "status_counts": {},
                "profile_counts": {},
                "most_relaxed": [],
                "avg_recipes_per_generation": 0,
            }

        from collections import Counter

        durations = [row["duration_ms"] for row in rows]
        recipe_counts = [row["recipe_count"] for row in rows]
        status_counts = Counter(row["status"] for row in rows)
        profile_counts = Counter(row["profile_name"] for row in rows)

        relaxed_counter: Counter[str] = Counter()
        slack_totals: Dict[str, float] = {}
        for row in rows:
            meta = parse_json_col(row["metadata"], {})
            for rc in meta.get("relaxed_constraints", []) if meta else []:
                label = rc.get("label", "")
                relaxed_counter[label] += 1
                slack_totals[label] = slack_totals.get(label, 0) + rc.get("slack_value", 0)

        most_relaxed = sorted(
            [
                {
                    "label": label,
                    "times_relaxed": count,
                    "avg_slack": round(slack_totals[label] / count, 2),
                    "total_generations": total,
                    "relaxation_rate": round(count / total, 3),
                }
                for label, count in relaxed_counter.items()
            ],
            key=lambda x: x["times_relaxed"],
            reverse=True,
        )[:20]

        return {
            "total_generations": total,
            "avg_duration_ms": round(sum(durations) / total),
            "status_counts": dict(status_counts),
            "profile_counts": dict(profile_counts),
            "most_relaxed": most_relaxed,
            "avg_recipes_per_generation": round(sum(recipe_counts) / total, 1),
        }

    def clear(self, user_id: int) -> None:
        """Delete all history entries for a user."""
        self._conn.execute("DELETE FROM generation_history WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def trim(self, user_id: int, max_entries: int = 100) -> None:
        """Remove oldest entries beyond max_entries."""
        self._conn.execute(
            "DELETE FROM generation_history WHERE user_id = ? AND id NOT IN "
            "(SELECT id FROM generation_history WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, max_entries),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "profile_name": row["profile_name"],
            "recipe_count": row["recipe_count"],
            "duration_ms": row["duration_ms"],
            "status": row["status"],
            "generated_at": row["generated_at"],
            "metadata": parse_json_col(row["metadata"]),
        }
