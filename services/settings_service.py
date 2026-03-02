from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

from constants import (
    API_CACHE_TTL_MINUTES,
    DEFAULT_MAX_DISCOVER_GENS,
    DEFAULT_MAX_PREVIOUS_RECIPES,
    DEFAULT_MENU_POLL_SECONDS,
    DEFAULT_TOAST_SECONDS,
)
from utils import atomic_write_json

# Keys that are exposed via the public endpoint (user-visible)
PUBLIC_KEYS = frozenset({
    "orders_enabled",
    "ratings_enabled",
    "show_ratings",
    "show_ingredients",
    "show_descriptions",
    "save_orders_to_tandoor",
    "order_meal_type_id",
    "save_ratings_to_tandoor",
    "theme",
    "kiosk_enabled",
    "kiosk_gesture",
    "kiosk_pin_enabled",
    "admin_pin_enabled",
    "meal_plan_enabled",
    "app_name",
    "slogan_header",
    "slogan_footer",
    "logo_url",
    "favicon_url",
    "loading_icon_url",
    "favicon_use_logo",
    "loading_icon_use_logo",
    "show_logo",
    "menu_poll_seconds",
    "toast_seconds",
    "max_discover_generations",
    "max_previous_recipes",
    "item_noun",
})

DEFAULTS: Dict[str, Any] = {
    "orders_enabled": False,
    "ratings_enabled": True,
    "show_ratings": True,
    "show_ingredients": True,
    "show_descriptions": True,
    "save_orders_to_tandoor": True,
    "order_meal_type_id": None,
    "save_ratings_to_tandoor": True,
    "theme": "cast-iron",
    "kiosk_enabled": False,
    "kiosk_gesture": "menu",
    "kiosk_pin": "",
    "kiosk_pin_enabled": False,
    "admin_pin_enabled": False,
    "api_cache_minutes": API_CACHE_TTL_MINUTES,
    "meal_plan_enabled": False,
    "app_name": "Morsl",
    "slogan_header": "a menu generator for Tandoor Recipes",
    "slogan_footer": "",
    "logo_url": "",
    "favicon_url": "",
    "loading_icon_url": "",
    "favicon_use_logo": False,
    "loading_icon_use_logo": False,
    "show_logo": True,
    "menu_poll_seconds": DEFAULT_MENU_POLL_SECONDS,
    "toast_seconds": DEFAULT_TOAST_SECONDS,
    "max_discover_generations": DEFAULT_MAX_DISCOVER_GENS,
    "max_previous_recipes": DEFAULT_MAX_PREVIOUS_RECIPES,
    "item_noun": "",
    "tandoor_url": "",
    "tandoor_token_b64": "",
}


class SettingsService:
    """Persists admin settings to a JSON file."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._lock = threading.Lock()
        self._settings: Dict[str, Any] = dict(DEFAULTS)
        self._load()

    def get_all(self) -> Dict[str, Any]:
        """Return all settings (admin view)."""
        with self._lock:
            return dict(self._settings)

    def get_public(self) -> Dict[str, Any]:
        """Return only customer-visible settings."""
        with self._lock:
            return {k: v for k, v in self._settings.items() if k in PUBLIC_KEYS}

    # Numeric settings with (min, max) bounds — validated in update()
    _BOUNDS: Dict[str, tuple] = {
        "menu_poll_seconds": (10, 300),
        "toast_seconds": (1, 10),
        "max_discover_generations": (1, 50),
        "max_previous_recipes": (10, 200),
    }

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Merge updates into settings and persist. Ignores unknown keys."""
        with self._lock:
            valid = {k: v for k, v in updates.items() if k in DEFAULTS}
            for key, (lo, hi) in self._BOUNDS.items():
                if key in valid:
                    try:
                        valid[key] = max(lo, min(hi, int(valid[key])))
                    except (TypeError, ValueError):
                        valid[key] = DEFAULTS[key]
            self._settings.update(valid)
            self._save()
            return dict(self._settings)

    def _save(self) -> None:
        path = os.path.join(self.data_dir, "settings.json")
        atomic_write_json(path, self._settings)

    def migrate_default_profile(self, config_service) -> None:
        """Migrate default_profile setting to a profile attribute."""
        with self._lock:
            value = self._settings.pop("default_profile", None)
            if value:
                config_service.set_default_profile(value)
                self._save()

    def _load(self) -> None:
        path = os.path.join(self.data_dir, "settings.json")
        if os.path.isfile(path):
            with open(path) as f:
                stored = json.load(f)
            # Merge stored over defaults so new keys get their defaults
            self._settings.update(stored)
