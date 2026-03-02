from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from slugify import slugify

from utils import atomic_write_json


class CategoryService:
    """Manages menu categories with JSON file persistence."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._categories: Dict[str, Dict[str, Any]] = {}
        self._load()

    def list_categories(self) -> List[Dict[str, Any]]:
        """Return all categories sorted by sort_order then id."""
        return sorted(
            self._categories.values(),
            key=lambda c: (c.get("sort_order", 0), c["id"]),
        )

    def create_category(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new category. Auto-generates id from display_name if not provided."""
        cat_id = config.get("id") or slugify(config.get("display_name", "")) or "category"
        if not cat_id:
            raise ValueError("display_name is required")
        # Deduplicate id if already taken
        base_id = cat_id
        counter = 2
        while cat_id in self._categories:
            cat_id = f"{base_id}-{counter}"
            counter += 1
        sort_order = config.get("sort_order")
        if sort_order is None:
            existing = [c.get("sort_order", 0) for c in self._categories.values()]
            sort_order = max(existing, default=-1) + 1
        category = {
            "id": cat_id,
            "display_name": config.get("display_name", cat_id),
            "subtitle": config.get("subtitle", ""),
            "icon": config.get("icon", ""),
            "sort_order": sort_order,
        }
        self._categories[cat_id] = category
        self._save()
        return category

    def update_category(self, cat_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing category. Raises KeyError if not found."""
        if cat_id not in self._categories:
            raise KeyError(f"Category not found: {cat_id}")
        category = self._categories[cat_id]
        for key in ("display_name", "subtitle", "icon"):
            if key in config:
                category[key] = config[key]
        if config.get("sort_order") is not None:
            category["sort_order"] = config["sort_order"]
        self._save()
        return category

    def reorder_categories(self, ordered_ids: List[str]) -> List[Dict[str, Any]]:
        """Set sort_order based on position in the given id list."""
        for i, cat_id in enumerate(ordered_ids):
            if cat_id in self._categories:
                self._categories[cat_id]["sort_order"] = i
        self._save()
        return self.list_categories()

    def delete_category(self, cat_id: str) -> None:
        """Delete a category. Raises KeyError if not found."""
        if cat_id not in self._categories:
            raise KeyError(f"Category not found: {cat_id}")
        del self._categories[cat_id]
        self._save()

    def _save(self) -> None:
        path = os.path.join(self.data_dir, "categories.json")
        atomic_write_json(path, self._categories)

    def _load(self) -> None:
        path = os.path.join(self.data_dir, "categories.json")
        if os.path.isfile(path):
            with open(path) as f:
                self._categories = json.load(f)
            self._migrate_categories()
        else:
            self._categories = {}
            self._save()

    def _migrate_categories(self) -> None:
        """Rename food-oriented category IDs back to cocktail-era ones."""
        id_remap = {
            "by-cuisine": "by-spirit",
            "by-meal": "by-style",
        }
        display_fixes = {
            "by-spirit": {
                "old_names": {"By Cuisine", "By Meal"},
                "display_name": "By Spirit",
                "subtitle": "Whiskey, Gin, Rum...",
                "icon": "bowl",
            },
            "by-style": {
                "old_names": {"By Cuisine", "By Meal"},
                "display_name": "By Style",
                "subtitle": "Martini, Negroni, Sour...",
                "icon": "dinner",
            },
        }
        changed = False
        for old_id, new_id in id_remap.items():
            if old_id in self._categories and new_id not in self._categories:
                cat = self._categories.pop(old_id)
                cat["id"] = new_id
                fix = display_fixes[new_id]
                cat["display_name"] = fix["display_name"]
                cat["subtitle"] = fix["subtitle"]
                cat["icon"] = fix["icon"]
                self._categories[new_id] = cat
                changed = True
        # Fix display names on already-renamed categories
        for cat_id, fix in display_fixes.items():
            cat = self._categories.get(cat_id)
            if cat and cat.get("display_name") in fix["old_names"]:
                cat["display_name"] = fix["display_name"]
                cat["subtitle"] = fix["subtitle"]
                cat["icon"] = fix["icon"]
                changed = True
        # Fix house-menu subtitle if blank
        hm = self._categories.get("house-menu")
        if hm and not hm.get("subtitle"):
            hm["subtitle"] = "Random cocktails"
            changed = True
        if changed:
            self._save()
