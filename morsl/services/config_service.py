from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from morsl.constants import API_CACHE_TTL_MINUTES, DEFAULT_CHOICES
from morsl.utils import atomic_write_json, safe_path

logger = logging.getLogger(__name__)

# Category IDs renamed in categories.json migration — remap in profiles too
_CATEGORY_REMAP = {"by-cuisine": "by-spirit", "by-meal": "by-style"}


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    choices: int
    constraint_count: int
    description: str = ""
    icon: str = ""
    category: str = ""
    default: bool = False
    show_on_menu: bool = True
    item_noun: str = ""


_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 _-]*$")


def _validate_profile_name(name: str) -> None:
    """Reject names that could escape the profiles directory."""
    if not _PROFILE_NAME_RE.match(name):
        raise ValueError(f"Invalid profile name: {name!r}")


class ConfigService:
    """Loads and manages menu generation profiles (v2 JSON format)."""

    def __init__(self, profiles_dir: str = "data/profiles") -> None:
        self.profiles_dir = profiles_dir
        self._profiles_cache: Optional[List[ProfileInfo]] = None
        self._migrate_profile_categories()

    def _migrate_profile_categories(self) -> None:
        """Rewrite profile files that use old category IDs."""
        if not os.path.isdir(self.profiles_dir):
            return
        for filename in sorted(os.listdir(self.profiles_dir)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.profiles_dir, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                old_cat = data.get("category", "")
                if old_cat in _CATEGORY_REMAP:
                    data["category"] = _CATEGORY_REMAP[old_cat]
                    atomic_write_json(path, data)
                    logger.info(
                        "Migrated profile %s category %s → %s", filename, old_cat, data["category"]
                    )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping profile migration for %s: %s", filename, e)

    # ---- Profile CRUD ----

    def create_profile(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new profile. Raises if it already exists."""
        _validate_profile_name(name)
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if os.path.isfile(json_path):
            raise FileExistsError(f"Profile already exists: {name}")
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._write_json(json_path, config)
        self._invalidate_profiles_cache()
        return self._apply_defaults(config)

    def update_profile(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing profile."""
        _validate_profile_name(name)
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Profile not found: {name}")
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._write_json(json_path, config)
        self._invalidate_profiles_cache()
        return self._apply_defaults(config)

    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        _validate_profile_name(name)
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Profile not found: {name}")
        os.unlink(json_path)
        self._invalidate_profiles_cache()

    # ---- Loading ----

    def load_profile(self, name: str) -> Dict[str, Any]:
        """Load a profile by name, merging with base.json if it exists."""
        _validate_profile_name(name)
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Profile not found: {json_path}")

        with open(json_path) as f:
            profile_config = json.load(f)

        # Merge with base.json if it exists and this isn't base itself
        base_path = os.path.join(self.profiles_dir, "base.json")
        if name != "base" and os.path.isfile(base_path):
            with open(base_path) as f:
                base_config = json.load(f)
            profile_config = self._merge_with_base(base_config, profile_config)

        return self._apply_defaults(profile_config)

    def get_profile_raw(self, name: str) -> Dict[str, Any]:
        """Load a profile's raw config without base merging or defaults."""
        _validate_profile_name(name)
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Profile not found: {name}")
        with open(json_path) as f:
            return json.load(f)

    def _invalidate_profiles_cache(self) -> None:
        self._profiles_cache = None

    def list_profiles(self) -> List[ProfileInfo]:
        """Scan profiles directory and return metadata for each profile (cached)."""
        if self._profiles_cache is not None:
            return list(self._profiles_cache)
        profiles: List[ProfileInfo] = []
        if not os.path.isdir(self.profiles_dir):
            return profiles

        # Read base.json once for all profiles
        base_config = None
        base_path = os.path.join(self.profiles_dir, "base.json")
        if os.path.isfile(base_path):
            with open(base_path) as f:
                base_config = json.load(f)

        for filename in sorted(os.listdir(self.profiles_dir)):
            if not filename.endswith(".json"):
                continue
            name = Path(filename).stem
            if name == "base":
                continue
            try:
                raw = self.get_profile_raw(name)
                is_default = raw.get("default", False)
                config = dict(raw)
                if base_config is not None:
                    config = self._merge_with_base(base_config, config)
                config = self._apply_defaults(config)
                choices = int(config.get("choices", DEFAULT_CHOICES))
                constraint_count = len(config.get("constraints", []))
                description = config.get("description", "")
                profiles.append(
                    ProfileInfo(
                        name=name,
                        choices=choices,
                        constraint_count=constraint_count,
                        description=description,
                        icon=config.get("icon", ""),
                        category=_CATEGORY_REMAP.get(
                            config.get("category", ""), config.get("category", "")
                        ),
                        default=is_default,
                        show_on_menu=config.get("show_on_menu", True),
                        item_noun=config.get("item_noun", ""),
                    )
                )
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.warning(f"Skipping profile '{name}': {e}")
                continue

        self._profiles_cache = profiles
        return list(profiles)

    def set_default_profile(self, name: str) -> None:
        """Mark a profile as default, clearing the flag from all others."""
        if not os.path.isdir(self.profiles_dir):
            return
        for filename in os.listdir(self.profiles_dir):
            if not filename.endswith(".json"):
                continue
            pname = Path(filename).stem
            if pname == "base":
                continue
            json_path = os.path.join(self.profiles_dir, filename)
            try:
                with open(json_path) as f:
                    data = json.load(f)
                if pname == name:
                    if not data.get("default"):
                        data["default"] = True
                        self._write_json(json_path, data)
                else:
                    if data.pop("default", None):
                        self._write_json(json_path, data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to update default flag for '{pname}': {e}")
        self._invalidate_profiles_cache()

    def clear_default_profile(self, name: str) -> None:
        """Remove the default flag from a single profile."""
        json_path = safe_path(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(json_path):
            return
        try:
            with open(json_path) as f:
                data = json.load(f)
            if data.pop("default", None):
                self._write_json(json_path, data)
                self._invalidate_profiles_cache()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to clear default flag for '{name}': {e}")

    @staticmethod
    def _merge_with_base(base: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a profile with base config.

        Profile values override base values. Constraints are concatenated
        (base constraints first, then profile constraints).
        """
        merged = {**base}
        base_constraints = base.get("constraints", [])
        profile_constraints = profile.get("constraints", [])

        merged.update(profile)

        # Concatenate constraints instead of overwriting
        if base_constraints or profile_constraints:
            merged["constraints"] = base_constraints + profile_constraints

        return merged

    @staticmethod
    def _apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply defaults for required fields."""
        config.setdefault("choices", DEFAULT_CHOICES)
        config.setdefault("cache", API_CACHE_TTL_MINUTES)
        config.setdefault("min_choices", None)
        config.setdefault("constraints", [])
        config.setdefault("show_on_menu", True)
        return config

    @staticmethod
    def _write_json(path: str, config: Dict[str, Any]) -> None:
        """Write config dict to JSON file atomically."""
        atomic_write_json(path, config)
