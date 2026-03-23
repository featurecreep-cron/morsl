from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from morsl.constants import API_CACHE_TTL_MINUTES, GENERATION_SHUTDOWN_TIMEOUT
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationState
from morsl.services.menu_service import MenuService
from morsl.services.recipe_detail_service import fetch_recipe_details
from morsl.services.template_service import TemplateService
from morsl.tandoor_api import TandoorAPI
from morsl.utils import atomic_write_json, now, safe_path

logger = logging.getLogger(__name__)

_VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _distribute_to_slots(
    expanded: Dict[str, list],
    profile_recipes: Dict[str, list],
    detail_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Distribute solved recipes into day/meal slots in solver output order."""
    profile_queues: Dict[str, deque] = {}
    for profile_name, recipes in profile_recipes.items():
        profile_queues[profile_name] = deque(
            detail_map[r.id] for r in recipes if r.id in detail_map
        )

    days_result: Dict[str, Dict[str, Any]] = {}
    for date_str in sorted(expanded.keys()):
        day_of_week = _DAY_NAMES[date.fromisoformat(date_str).weekday()]
        day_meals: Dict[str, Dict[str, Any]] = {}

        for assignment in expanded[date_str]:
            queue = profile_queues.get(assignment["profile"], deque())
            slot_recipes = [queue.popleft() for _ in range(assignment["recipes_per_day"]) if queue]
            day_meals[str(assignment["meal_type_id"])] = {
                "meal_type_name": assignment["meal_type_name"],
                "profile": assignment["profile"],
                "recipes": slot_recipes,
            }

        days_result[date_str] = {
            "day_of_week": day_of_week,
            "meals": day_meals,
        }
    return days_result


def _validate_template_name(name: str) -> None:
    """Reject names that could escape the plans directory (path traversal)."""
    if not name or not _VALID_NAME_RE.match(name):
        raise ValueError(f"Invalid template name: {name}")


@dataclass
class WeeklyGenerationStatus:
    state: GenerationState = GenerationState.IDLE
    request_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    template: Optional[str] = None
    profile_progress: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class WeeklyGenerationService:
    """Orchestrates multi-profile generation across a weekly template."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self.plans_dir = os.path.join(data_dir, "weekly_plans")
        self._status = WeeklyGenerationStatus()
        self._current_task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()

    def get_status(self) -> WeeklyGenerationStatus:
        return self._status

    def get_plan(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Load a generated weekly plan from disk."""
        _validate_template_name(template_name)
        path = safe_path(self.plans_dir, f"{template_name}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted weekly plan file: %s", path)
            return None

    def clear_plan(self, template_name: str) -> bool:
        """Delete a weekly plan file. Returns True if removed."""
        _validate_template_name(template_name)
        path = safe_path(self.plans_dir, f"{template_name}.json")
        if os.path.isfile(path):
            os.unlink(path)
            return True
        return False

    async def start_generation(
        self,
        template_name: str,
        template_service: TemplateService,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        week_start: Optional[date] = None,
        generation_service: Optional[Any] = None,
        settings_service: Optional[Any] = None,
    ) -> str:
        """Start weekly generation in the background. Returns request_id."""
        async with self._lock:
            if self._status.state == GenerationState.GENERATING:
                raise RuntimeError("A weekly generation is already in progress")

            # Check single-menu generation isn't running
            if (
                generation_service
                and generation_service.get_status().state == GenerationState.GENERATING
            ):
                raise RuntimeError("A single-menu generation is in progress")

            request_id = str(uuid4())
            self._status = WeeklyGenerationStatus(
                state=GenerationState.GENERATING,
                request_id=request_id,
                started_at=now(),
                template=template_name,
            )

            if week_start is None:
                today = date.today()
                week_start = today - timedelta(days=today.weekday())

            loop = asyncio.get_running_loop()
            self._current_task = loop.create_task(
                self._run_generation(
                    template_name,
                    template_service,
                    config_service,
                    url,
                    token,
                    app_logger,
                    week_start,
                    settings_service,
                )
            )
            return request_id

    async def _run_generation(
        self,
        template_name: str,
        template_service: TemplateService,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        week_start: date,
        settings_service: Optional[Any] = None,
    ) -> None:
        """Run the multi-profile generation in a thread pool and save results."""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_generate,
                template_name,
                template_service,
                config_service,
                url,
                token,
                app_logger,
                week_start,
                settings_service,
            )

            self._save_plan(template_name, result)
            self._status.state = GenerationState.COMPLETE
            self._status.completed_at = now()
            self._status.warnings = result.get("warnings", [])

        except Exception as e:
            logger.warning("Weekly generation failed", exc_info=True)
            self._status.state = GenerationState.ERROR
            self._status.completed_at = now()
            self._status.error = str(e)

    def _generate_for_profile(
        self,
        profile_name: str,
        total_needed: int,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        cache_minutes: int,
        deduplicate: bool,
        exclude_ids: set,
    ) -> Dict[str, Any]:
        """Generate recipes for a single profile, returning results and warnings."""
        self._status.profile_progress[profile_name] = "generating"
        warnings: List[str] = []

        try:
            config = config_service.load_profile(profile_name)
        except FileNotFoundError:
            msg = f"Profile '{profile_name}' not found, skipping"
            self._status.profile_progress[profile_name] = "error"
            return {
                "slot_result": {"status": "error", "warnings": [msg]},
                "warnings": [msg],
                "recipes": None,
            }

        config["choices"] = total_needed
        config["cache"] = cache_minutes

        service = MenuService(url=url, token=token, config=config, logger=app_logger)
        service.prepare_data()

        if deduplicate and exclude_ids:
            original_count = len(service.recipes)
            service.recipes = [r for r in service.recipes if r.id not in exclude_ids]
            if len(service.recipes) < original_count:
                app_logger.info(
                    "Dedup: filtered %d recipes from pool for profile '%s'",
                    original_count - len(service.recipes),
                    profile_name,
                )

        if len(service.recipes) < total_needed:
            msg = (
                f"Profile '{profile_name}': only "
                f"{len(service.recipes)} recipes available, "
                f"{total_needed} requested"
            )
            warnings.append(msg)
            if len(service.recipes) == 0:
                self._status.profile_progress[profile_name] = "error"
                return {
                    "slot_result": {"status": "error", "warnings": [msg]},
                    "warnings": warnings,
                    "recipes": None,
                }
            service.choices = len(service.recipes)

        solver_result = service.select_recipes()
        if solver_result.warnings:
            warnings.extend(solver_result.warnings)

        self._status.profile_progress[profile_name] = "complete"
        return {
            "slot_result": {"status": solver_result.status, "warnings": solver_result.warnings},
            "warnings": warnings,
            "recipes": list(solver_result.recipes),
        }

    def _sync_generate(
        self,
        template_name: str,
        template_service: TemplateService,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        week_start: date,
        settings_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Synchronous multi-profile generation — runs in thread pool."""
        template = template_service.get_template(template_name)
        deduplicate = template.get("deduplicate", True)

        # 1. Expand slots to date-based assignments
        expanded = template_service.expand_slots(template, week_start)

        # 2. Get generation plan: {profile: total_recipes_needed}
        gen_plan = template_service.get_generation_plan(template)

        # Sort smallest-pool-first for better dedup
        sorted_profiles = sorted(gen_plan.items(), key=lambda x: x[1])

        # Get global cache setting
        cache_minutes = API_CACHE_TTL_MINUTES
        if settings_service:
            try:
                app_settings = settings_service.get_all()
                cache_minutes = app_settings.get("api_cache_minutes", API_CACHE_TTL_MINUTES)
            except Exception:  # noqa: S110
                pass

        # 3. Run each profile sequentially for dedup
        all_warnings: List[str] = []
        exclude_ids: set = set()
        profile_recipes: Dict[str, list] = {}
        slot_results: Dict[str, Dict[str, Any]] = {}

        for profile_name, total_needed in sorted_profiles:
            result = self._generate_for_profile(
                profile_name,
                total_needed,
                config_service,
                url,
                token,
                app_logger,
                cache_minutes,
                deduplicate,
                exclude_ids,
            )
            slot_results[profile_name] = result["slot_result"]
            all_warnings.extend(result["warnings"])
            if result["recipes"] is not None:
                profile_recipes[profile_name] = result["recipes"]
                if deduplicate:
                    exclude_ids.update(r.id for r in result["recipes"])

        # 4. Fetch recipe details for ALL selected recipes
        all_recipe_objs = []
        for recipes in profile_recipes.values():
            all_recipe_objs.extend(recipes)

        api = TandoorAPI(url, token, app_logger, cache=cache_minutes)
        details_list = fetch_recipe_details(api, all_recipe_objs, app_logger)

        detail_map: Dict[int, Dict[str, Any]] = {}
        for detail in details_list:
            detail_map[detail["id"]] = detail

        # 5. Distribute recipes to day/meal slots
        days_result = _distribute_to_slots(
            expanded,
            profile_recipes,
            detail_map,
        )

        return {
            "template": template_name,
            "generated_at": now().isoformat(),
            "week_start": week_start.isoformat(),
            "days": days_result,
            "slot_results": slot_results,
            "warnings": all_warnings,
        }

    async def regenerate_slot(
        self,
        template_name: str,
        target_date: str,
        meal_type_id: int,
        template_service: TemplateService,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        settings_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Regenerate a single slot in an existing weekly plan."""
        plan = self.get_plan(template_name)
        if not plan:
            raise FileNotFoundError(f"No weekly plan found for template '{template_name}'")

        day_data = plan.get("days", {}).get(target_date)
        if not day_data:
            raise ValueError(f"Date '{target_date}' not found in plan")

        mt_key = str(meal_type_id)
        meal_data = day_data.get("meals", {}).get(mt_key)
        if not meal_data:
            raise ValueError(f"Meal type {meal_type_id} not found on {target_date}")

        profile_name = meal_data["profile"]
        recipes_per_day = len(meal_data.get("recipes", [])) or 1

        # Compute exclude set: all recipe IDs in plan EXCEPT target slot
        target_ids = {r["id"] for r in meal_data.get("recipes", []) if "id" in r}
        exclude_ids: set = set()
        for day in plan.get("days", {}).values():
            for meal in day.get("meals", {}).values():
                for r in meal.get("recipes", []):
                    if r.get("id") and r["id"] not in target_ids:
                        exclude_ids.add(r["id"])

        # Get global cache setting
        cache_minutes = API_CACHE_TTL_MINUTES
        if settings_service:
            try:
                app_settings = settings_service.get_all()
                cache_minutes = app_settings.get("api_cache_minutes", API_CACHE_TTL_MINUTES)
            except Exception:  # noqa: S110
                pass

        loop = asyncio.get_running_loop()
        new_recipes = await loop.run_in_executor(
            None,
            self._sync_regenerate_slot,
            profile_name,
            recipes_per_day,
            exclude_ids,
            config_service,
            url,
            token,
            app_logger,
            cache_minutes,
        )

        # Swap into plan and save
        meal_data["recipes"] = new_recipes
        self._save_plan(template_name, plan)
        return plan

    def _sync_regenerate_slot(
        self,
        profile_name: str,
        recipes_per_day: int,
        exclude_ids: set,
        config_service: ConfigService,
        url: str,
        token: str,
        app_logger: logging.Logger,
        cache_minutes: int,
    ) -> List[Dict[str, Any]]:
        """Single-slot regeneration — runs in thread pool."""
        config = config_service.load_profile(profile_name)
        config["choices"] = recipes_per_day
        config["cache"] = cache_minutes

        service = MenuService(url=url, token=token, config=config, logger=app_logger)
        service.prepare_data()

        if exclude_ids:
            service.recipes = [r for r in service.recipes if r.id not in exclude_ids]

        if len(service.recipes) < recipes_per_day:
            if len(service.recipes) == 0:
                raise RuntimeError(
                    f"No recipes available for profile '{profile_name}' after dedup"
                )
            service.choices = len(service.recipes)

        solver_result = service.select_recipes()

        api = TandoorAPI(url, token, app_logger, cache=cache_minutes)
        return fetch_recipe_details(api, solver_result.recipes, app_logger)

    async def wait_for_completion(self, timeout: float = 300.0) -> WeeklyGenerationStatus:
        """Wait for an in-flight generation to finish."""
        if self._current_task and not self._current_task.done():
            await asyncio.wait_for(asyncio.shield(self._current_task), timeout)
        return self._status

    async def shutdown(self, timeout: float = GENERATION_SHUTDOWN_TIMEOUT) -> None:
        """Cancel any in-flight generation task and wait for cleanup."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(self._current_task), timeout=timeout)
            self._status.state = GenerationState.IDLE

    def _save_plan(self, template_name: str, plan_data: Dict[str, Any]) -> None:
        """Atomic write of weekly plan."""
        _validate_template_name(template_name)
        os.makedirs(self.plans_dir, exist_ok=True)
        path = safe_path(self.plans_dir, f"{template_name}.json")
        atomic_write_json(path, plan_data)
