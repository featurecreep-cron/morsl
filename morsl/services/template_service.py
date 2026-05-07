from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from morsl.repositories.template import TemplateRepository

logger = logging.getLogger(__name__)

_VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_VALID_DAYS = frozenset({"mon", "tue", "wed", "thu", "fri", "sat", "sun"})
_DAY_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class TemplateService:
    """CRUD and expansion for weekly meal-plan templates."""

    def __init__(
        self,
        repo: Optional[TemplateRepository] = None,
        user_id: int = 1,
        data_dir: str = "data",
    ) -> None:
        if repo is not None:
            self._repo = repo
        else:
            from morsl.db import ensure_default_user, get_db

            conn = get_db(data_dir)
            ensure_default_user(conn, user_id)
            self._repo = TemplateRepository(conn)
        self._user_id = user_id

    # ---- Name validation ----

    @staticmethod
    def _validate_name(name: str) -> None:
        """Reject names that could escape templates_dir (path traversal)."""
        if not name or not _VALID_NAME_RE.match(name):
            raise ValueError(f"Invalid template name: {name}")

    # ---- CRUD ----

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return summary info for all templates."""
        rows = self._repo.list_all(self._user_id)
        templates: List[Dict[str, Any]] = []
        for row in rows:
            config = row["config"]
            templates.append(
                {
                    "name": row["name"],
                    "description": config.get("description", ""),
                    "slot_count": len(config.get("slots", [])),
                    "deduplicate": config.get("deduplicate", True),
                }
            )
        return templates

    def get_template(self, name: str) -> Dict[str, Any]:
        """Load a single template by name."""
        self._validate_name(name)
        row = self._repo.get_by_name(self._user_id, name)
        if row is None:
            raise FileNotFoundError(f"Template not found: {name}")
        config = row["config"]
        config["name"] = name
        return config

    def create_template(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new template. Raises FileExistsError if already exists."""
        self._validate_name(name)
        if self._repo.exists(self._user_id, name):
            raise FileExistsError(f"Template already exists: {name}")
        config["name"] = name
        self._repo.create(self._user_id, name, config)
        return config

    def update_template(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing template."""
        self._validate_name(name)
        if not self._repo.exists(self._user_id, name):
            raise FileNotFoundError(f"Template not found: {name}")
        config["name"] = name
        self._repo.update(self._user_id, name, config)
        return config

    def delete_template(self, name: str) -> None:
        """Delete a template."""
        self._validate_name(name)
        if not self._repo.delete(self._user_id, name):
            raise FileNotFoundError(f"Template not found: {name}")

    # ---- Validation ----

    def validate_template(self, config: Dict[str, Any], config_service: Any) -> List[str]:
        """Validate a template config. Returns list of error strings (empty = valid)."""
        errors: List[str] = []
        slots = config.get("slots")
        if not slots or not isinstance(slots, list):
            errors.append("Template must have at least one slot")
            return errors

        profile_names = {p.name for p in config_service.list_profiles()}

        for i, slot in enumerate(slots):
            days = slot.get("days", [])
            if not days:
                errors.append(f"Slot {i}: must specify at least one day")
            for d in days:
                if d not in _VALID_DAYS:
                    errors.append(f"Slot {i}: invalid day '{d}'")

            profile = slot.get("profile")
            if not profile:
                errors.append(f"Slot {i}: profile is required")
            elif profile not in profile_names:
                errors.append(f"Slot {i}: profile '{profile}' not found")

            if not slot.get("meal_type_id"):
                errors.append(f"Slot {i}: meal_type_id is required")

            rpd = slot.get("recipes_per_day", 1)
            if not isinstance(rpd, int) or rpd < 1:
                errors.append(f"Slot {i}: recipes_per_day must be >= 1")

        return errors

    # ---- Expansion ----

    def expand_slots(
        self, template: Dict[str, Any], week_start: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Resolve day names to calendar dates.

        week_start must be a Monday. Returns {date_str: [SlotAssignment, ...]}
        where each SlotAssignment is:
        {"meal_type_id": int, "meal_type_name": str, "profile": str, "recipes_per_day": int}
        """
        if week_start.weekday() != 0:
            raise ValueError(
                f"week_start must be a Monday, got "
                f"{week_start.isoformat()} ({week_start.strftime('%A')})"
            )
        result: Dict[str, List[Dict[str, Any]]] = {}
        for slot in template.get("slots", []):
            days = slot.get("days", [])
            profile = slot.get("profile", "")
            meal_type_id = slot.get("meal_type_id")
            meal_type_name = slot.get("meal_type_name", "")
            recipes_per_day = slot.get("recipes_per_day", 1)

            for day_name in days:
                day_offset = _DAY_INDEX[day_name]
                actual_date = week_start + timedelta(days=day_offset)
                date_str = actual_date.isoformat()

                assignment = {
                    "meal_type_id": meal_type_id,
                    "meal_type_name": meal_type_name,
                    "profile": profile,
                    "recipes_per_day": recipes_per_day,
                }

                result.setdefault(date_str, []).append(assignment)

        return result

    def get_generation_plan(self, template: Dict[str, Any]) -> Dict[str, int]:
        """Group slots by profile and compute total recipes needed per profile.

        Returns {profile_name: total_recipes_needed}.
        """
        plan: Dict[str, int] = {}
        for slot in template.get("slots", []):
            profile = slot.get("profile", "")
            num_days = len(slot.get("days", []))
            recipes_per_day = slot.get("recipes_per_day", 1)
            plan[profile] = plan.get(profile, 0) + (num_days * recipes_per_day)
        return plan
