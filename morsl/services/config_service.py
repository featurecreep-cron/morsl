from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from morsl.constants import API_CACHE_TTL_MINUTES, DEFAULT_CHOICES
from morsl.repositories.profile import ProfileRepository

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
    """Loads and manages menu generation profiles (SQLite-backed)."""

    def __init__(
        self,
        repo: Optional[ProfileRepository] = None,
        user_id: int = 1,
        data_dir: str = "data",
        profiles_dir: Optional[str] = None,
    ) -> None:
        if repo is not None:
            self._repo = repo
        else:
            from morsl.db import ensure_default_user, get_db

            conn = get_db(data_dir)
            ensure_default_user(conn, user_id)
            self._repo = ProfileRepository(conn)
        self._user_id = user_id
        self._profiles_cache: Optional[List[ProfileInfo]] = None
        self._migrate_profile_categories()

    def _migrate_profile_categories(self) -> None:
        """Rewrite profiles that use old category IDs."""
        profiles = self._repo.list_all(self._user_id)
        for p in profiles:
            config = p["config"]
            old_cat = config.get("category", "")
            if old_cat in _CATEGORY_REMAP:
                config["category"] = _CATEGORY_REMAP[old_cat]
                self._repo.update(self._user_id, p["name"], config)
                logger.info(
                    "Migrated profile %s category %s → %s",
                    p["name"],
                    old_cat,
                    config["category"],
                )

    # ---- Profile CRUD ----

    def create_profile(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new profile. Raises if it already exists."""
        _validate_profile_name(name)
        if self._repo.exists(self._user_id, name):
            raise FileExistsError(f"Profile already exists: {name}")
        is_default = config.pop("default", False)
        self._repo.create(self._user_id, name, config, is_default=bool(is_default))
        self._invalidate_profiles_cache()
        return self._apply_defaults(config)

    def update_profile(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing profile."""
        _validate_profile_name(name)
        if not self._repo.exists(self._user_id, name):
            raise FileNotFoundError(f"Profile not found: {name}")
        self._repo.update(self._user_id, name, config)
        self._invalidate_profiles_cache()
        return self._apply_defaults(config)

    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        _validate_profile_name(name)
        if not self._repo.delete(self._user_id, name):
            raise FileNotFoundError(f"Profile not found: {name}")
        self._invalidate_profiles_cache()

    # ---- Loading ----

    def load_profile(self, name: str) -> Dict[str, Any]:
        """Load a profile by name, merging with base if it exists."""
        _validate_profile_name(name)
        row = self._repo.get_by_name(self._user_id, name)
        if row is None:
            raise FileNotFoundError(f"Profile not found: {name}")

        profile_config = dict(row["config"])

        # Merge with base profile if it exists and this isn't base itself
        if name != "base":
            base_row = self._repo.get_by_name(self._user_id, "base")
            if base_row is not None:
                profile_config = self._merge_with_base(base_row["config"], profile_config)

        return self._apply_defaults(profile_config)

    def get_profile_raw(self, name: str) -> Dict[str, Any]:
        """Load a profile's raw config without base merging or defaults."""
        _validate_profile_name(name)
        row = self._repo.get_by_name(self._user_id, name)
        if row is None:
            raise FileNotFoundError(f"Profile not found: {name}")
        config = dict(row["config"])
        if row["is_default"]:
            config["default"] = True
        return config

    def _invalidate_profiles_cache(self) -> None:
        self._profiles_cache = None

    def list_profiles(self) -> List[ProfileInfo]:
        """Return metadata for each profile (cached)."""
        if self._profiles_cache is not None:
            return list(self._profiles_cache)

        profiles: List[ProfileInfo] = []
        all_rows = self._repo.list_all(self._user_id)

        # Read base config once for all profiles
        base_config = None
        for row in all_rows:
            if row["name"] == "base":
                base_config = row["config"]
                break

        for row in all_rows:
            name = row["name"]
            if name == "base":
                continue
            try:
                raw = dict(row["config"])
                is_default = row["is_default"]
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
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping profile '{name}': {e}")
                continue

        self._profiles_cache = profiles
        return list(profiles)

    def set_default_profile(self, name: str) -> None:
        """Mark a profile as default, clearing the flag from all others."""
        self._repo.set_default(self._user_id, name)
        self._invalidate_profiles_cache()

    def clear_default_profile(self, name: str) -> None:
        """Remove the default flag from a single profile."""
        self._repo.clear_default(self._user_id, name)
        self._invalidate_profiles_cache()

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
