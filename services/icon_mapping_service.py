"""Manages keyword/food → icon mappings with JSON file persistence."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from utils import atomic_write_json


class IconMappingService:
    """Persists admin-configured keyword/food → icon-key mappings to data/icon-mappings.json."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._data: Dict[str, Dict[str, str]] = {"keyword_icons": {}, "food_icons": {}}
        self._load()

    def get_all(self) -> Dict[str, Any]:
        return self._data

    def update(self, keyword_icons: Dict[str, str], food_icons: Dict[str, str]) -> Dict[str, Any]:
        """Bulk-replace all mappings. Names stored lowercase for case-insensitive matching."""
        self._data["keyword_icons"] = {k.lower(): v for k, v in keyword_icons.items()}
        self._data["food_icons"] = {k.lower(): v for k, v in food_icons.items()}
        self._save()
        return self._data

    def _save(self) -> None:
        path = os.path.join(self.data_dir, "icon-mappings.json")
        atomic_write_json(path, self._data)

    def _load(self) -> None:
        path = os.path.join(self.data_dir, "icon-mappings.json")
        if os.path.isfile(path):
            with open(path) as f:
                raw = json.load(f)
            self._data = {
                "keyword_icons": raw.get("keyword_icons", {}),
                "food_icons": raw.get("food_icons", {}),
            }
        else:
            self._data = {"keyword_icons": {}, "food_icons": {}}
