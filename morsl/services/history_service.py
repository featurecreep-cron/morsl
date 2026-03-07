from __future__ import annotations

import json
import logging
import os
import threading
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from morsl.constants import MAX_HISTORY_ENTRIES
from morsl.utils import atomic_write_json

logger = logging.getLogger(__name__)


class HistoryService:
    """Persists generation history to a JSON file with in-memory cache."""

    MAX_ENTRIES = MAX_HISTORY_ENTRIES

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._load()

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """Prepend a new history entry and trim to MAX_ENTRIES."""
        with self._lock:
            self._entries.insert(0, entry)
            self._entries = self._entries[: self.MAX_ENTRIES]
            self._save()

    def list_entries(self, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Return paginated entries (newest first) and total count."""
        with self._lock:
            total = len(self._entries)
            return self._entries[offset : offset + limit], total

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a single history entry by ID."""
        with self._lock:
            for entry in self._entries:
                if entry.get("id") == entry_id:
                    return entry
            return None

    def get_analytics(self) -> Dict[str, Any]:
        """Compute constraint analytics from stored history."""
        with self._lock:
            entries = list(self._entries)
        total = len(entries)
        if total == 0:
            return {
                "total_generations": 0,
                "avg_duration_ms": 0,
                "status_counts": {},
                "profile_counts": {},
                "most_relaxed": [],
                "avg_recipes_per_generation": 0,
            }

        durations = [e.get("duration_ms", 0) for e in entries]
        recipe_counts = [e.get("recipe_count", 0) for e in entries]
        status_counts = Counter(e.get("status", "unknown") for e in entries)
        profile_counts = Counter(e.get("profile", "unknown") for e in entries)

        # Aggregate relaxed constraints across all generations
        relaxed_counter: Counter[str] = Counter()
        slack_totals: Dict[str, float] = {}
        for entry in entries:
            for rc in entry.get("relaxed_constraints", []):
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

    def clear(self) -> None:
        """Delete all history entries."""
        with self._lock:
            self._entries = []
            self._save()

    def _save(self) -> None:
        path = os.path.join(self.data_dir, "generation_history.json")
        atomic_write_json(path, self._entries)

    def _load(self) -> None:
        path = os.path.join(self.data_dir, "generation_history.json")
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._entries = data[: self.MAX_ENTRIES]
                else:
                    self._entries = []
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt generation_history.json — starting fresh")
                self._entries = []
