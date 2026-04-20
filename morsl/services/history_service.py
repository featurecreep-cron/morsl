from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from morsl.constants import MAX_HISTORY_ENTRIES
from morsl.repositories.history import HistoryRepository

logger = logging.getLogger(__name__)


class HistoryService:
    """Persists generation history via a HistoryRepository (SQLite-backed)."""

    MAX_ENTRIES = MAX_HISTORY_ENTRIES

    def __init__(
        self,
        repo: Optional[HistoryRepository] = None,
        user_id: int = 1,
        data_dir: str = "data",
    ) -> None:
        if repo is not None:
            self._repo = repo
        else:
            from morsl.db import ensure_default_user, get_db

            conn = get_db(data_dir)
            ensure_default_user(conn, user_id)
            self._repo = HistoryRepository(conn)
        self._user_id = user_id
        self._lock = threading.Lock()

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """Add a new history entry and trim to MAX_ENTRIES."""
        with self._lock:
            profile = entry.get("profile", "unknown")
            recipe_count = entry.get("recipe_count", 0)
            duration_ms = entry.get("duration_ms", 0)
            status = entry.get("status", "unknown")
            generated_at = entry.get("generated_at", "")

            # Store the full entry dict as metadata for round-trip fidelity
            self._repo.add_entry(
                self._user_id,
                profile_name=profile,
                recipe_count=recipe_count,
                duration_ms=duration_ms,
                status=status,
                generated_at=generated_at,
                metadata=entry,
            )
            self._repo.trim(self._user_id, self.MAX_ENTRIES)

    def list_entries(self, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Return paginated entries (newest first) and total count."""
        with self._lock:
            rows, total = self._repo.list_entries(self._user_id, limit, offset)
            return [self._row_to_entry(r) for r in rows], total

    def get_entry(self, entry_id: Any) -> Optional[Dict[str, Any]]:
        """Get a single history entry by ID."""
        with self._lock:
            # Accept integer DB IDs or string UUIDs stored in metadata
            if isinstance(entry_id, int):
                row = self._repo.get_entry(self._user_id, entry_id)
                return self._row_to_entry(row) if row else None
            # String ID: search in metadata
            rows, _ = self._repo.list_entries(self._user_id, limit=self.MAX_ENTRIES)
            for row in rows:
                entry = self._row_to_entry(row)
                if entry.get("id") == entry_id:
                    return entry
            return None

    def get_analytics(self) -> Dict[str, Any]:
        """Compute constraint analytics from stored history."""
        with self._lock:
            return self._repo.get_analytics(self._user_id)

    def clear(self) -> None:
        """Delete all history entries."""
        with self._lock:
            self._repo.clear(self._user_id)

    @staticmethod
    def _row_to_entry(row: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct a service-level entry dict from a repo row.

        If metadata contains the original entry dict, use it.
        Otherwise, build from structured columns.
        """
        meta = row.get("metadata")
        if isinstance(meta, dict) and "profile" in meta:
            # Full original entry was stored — use it, add the DB id
            entry = dict(meta)
            entry["_db_id"] = row["id"]
            return entry
        # Fallback: build from structured columns
        return {
            "id": row["id"],
            "profile": row["profile_name"],
            "recipe_count": row["recipe_count"],
            "duration_ms": row["duration_ms"],
            "status": row["status"],
            "generated_at": row["generated_at"],
        }
