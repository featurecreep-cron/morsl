from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from logging import Logger
from typing import Any, Dict, List, Optional
from uuid import uuid4

from morsl.constants import API_CACHE_TTL_MINUTES, DEFAULT_SOFT_WEIGHT, GENERATION_SHUTDOWN_TIMEOUT
from morsl.providers.tandoor import TandoorProvider
from morsl.repositories.menu import MenuRepository
from morsl.services.history_service import HistoryService
from morsl.services.menu_service import MenuService
from morsl.services.recipe_detail_service import fetch_recipe_details
from morsl.services.sse_publisher import SSEPublisher
from morsl.solver import RecipePicker
from morsl.tandoor_api import TandoorAPI
from morsl.utils import now


class GenerationState(str, Enum):
    IDLE = "idle"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class GenerationStatus:
    state: GenerationState = GenerationState.IDLE
    request_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    recipe_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)


class GenerationService(SSEPublisher):
    """Manages asynchronous menu generation with state tracking."""

    def __init__(
        self,
        data_dir: str = "data",
        history_service: Optional[HistoryService] = None,
        menu_repo: Optional[MenuRepository] = None,
        user_id: int = 1,
    ) -> None:
        self.data_dir = data_dir
        self._history_service = history_service
        self._user_id = user_id
        if menu_repo is not None:
            self._menu_repo = menu_repo
        else:
            from morsl.db import ensure_default_user, get_db

            conn = get_db(data_dir)
            ensure_default_user(conn, user_id)
            self._menu_repo = MenuRepository(conn)
        self._status = GenerationStatus()
        self._current_task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._cached_menu: Optional[Dict[str, Any]] = None
        self._init_sse()
        self._cleanup_stale_temp_files()
        # Load menu into cache on startup
        self._cached_menu = self._load_menu()

    def get_status(self) -> GenerationStatus:
        return self._status

    def get_current_menu(self) -> Optional[Dict[str, Any]]:
        """Return cached menu (loaded from disk on startup, updated on save/clear)."""
        return self._cached_menu

    def _load_menu(self) -> Optional[Dict[str, Any]]:
        """Load current menu from the database."""
        row = self._menu_repo.get_current(self._user_id)
        if row is None:
            return None
        # Reconstruct the menu dict format expected by the rest of the service
        menu = dict(row.get("metadata") or {})
        menu["recipes"] = row["recipes"]
        menu["generated_at"] = row["generated_at"]
        menu["profile"] = row["profile_name"]
        if "id" not in menu:
            menu["id"] = row["id"]
        menu["_db_id"] = row["id"]
        return menu

    def clear_menu(self) -> bool:
        """Clear the current menu. Returns True if a menu was cleared."""
        had_menu = self._cached_menu is not None
        self._cached_menu = None
        self._menu_repo.clear_current(self._user_id)
        if had_menu:
            self._notify_subscribers({"type": "menu_cleared"})
        return had_menu

    async def start_generation(
        self,
        config: Dict[str, Any],
        url: str,
        token: str,
        logger: Logger,
        profile_name: str = "default",
        clear_others: bool = False,
    ) -> str:
        """Start menu generation in the background. Returns request_id."""
        async with self._lock:
            if self._status.state == GenerationState.GENERATING:
                raise RuntimeError("A generation is already in progress")

            request_id = str(uuid4())
            self._status = GenerationStatus(
                state=GenerationState.GENERATING,
                request_id=request_id,
                started_at=now(),
            )
            self._notify_subscribers({"type": "generating"})

            loop = asyncio.get_running_loop()
            self._current_task = loop.create_task(
                self._run_generation(
                    config, url, token, logger, request_id, profile_name, clear_others
                )
            )
            return request_id

    async def _run_generation(
        self,
        config: Dict[str, Any],
        url: str,
        token: str,
        logger: Logger,
        request_id: str,
        profile_name: str = "default",
        clear_others: bool = False,
    ) -> None:
        """Run the solver in a thread pool and save results."""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._sync_generate, config, url, token, logger
            )

            result["profile"] = profile_name

            # Save to disk atomically
            self._save_menu(result, clear_others=clear_others)

            self._status.state = GenerationState.COMPLETE
            self._status.completed_at = now()
            self._status.recipe_count = len(result["recipes"])
            self._status.warnings = result.get("warnings", [])

            # Record in history
            if self._history_service:
                duration_ms = 0
                if self._status.started_at and self._status.completed_at:
                    delta = self._status.completed_at - self._status.started_at
                    duration_ms = int(delta.total_seconds() * 1000)
                self._history_service.add_entry(
                    {
                        "id": str(uuid4()),
                        "generated_at": result.get("generated_at", now().isoformat()),
                        "duration_ms": duration_ms,
                        "profile": profile_name,
                        "request_id": request_id,
                        "recipe_count": len(result["recipes"]),
                        "requested_count": result.get("requested_count", 0),
                        "constraint_count": result.get("constraint_count", 0),
                        "status": result.get("status", "unknown"),
                        "recipes": [{"id": r["id"], "name": r["name"]} for r in result["recipes"]],
                        "relaxed_constraints": result.get("relaxed_constraints", []),
                        "warnings": result.get("warnings", []),
                    }
                )

        except Exception as e:  # broad-except — state machine must capture any failure
            logger.warning("Menu generation failed", exc_info=True)
            self._status.state = GenerationState.ERROR
            self._status.completed_at = now()
            self._status.error = str(e)

            # Record failed generation in history
            if self._history_service:
                duration_ms = 0
                if self._status.started_at and self._status.completed_at:
                    delta = self._status.completed_at - self._status.started_at
                    duration_ms = int(delta.total_seconds() * 1000)
                self._history_service.add_entry(
                    {
                        "id": str(uuid4()),
                        "generated_at": now().isoformat(),
                        "duration_ms": duration_ms,
                        "profile": profile_name,
                        "request_id": request_id,
                        "recipe_count": 0,
                        "requested_count": int(config.get("choices", 0)),
                        "constraint_count": len(config.get("constraints", [])),
                        "status": "error",
                        "error": str(e),
                        "recipes": [],
                        "relaxed_constraints": [],
                        "warnings": [],
                    }
                )

    @staticmethod
    def _sync_generate(
        config: Dict[str, Any],
        url: str,
        token: str,
        logger: Logger,
    ) -> Dict[str, Any]:
        """Synchronous generation — runs in thread pool."""
        cache = int(config.get("cache", API_CACHE_TTL_MINUTES))
        api = TandoorAPI(url, token, logger, cache=cache)
        provider = TandoorProvider(api)
        service = MenuService(config=config, logger=logger, provider=provider)
        service.prepare_data()

        if len(service.recipes) < service.choices:
            raise RuntimeError(
                f"Not enough recipes: {len(service.recipes)} available, "
                f"{service.choices} requested"
            )

        solver_result = service.select_recipes()

        # Fetch full details (image + ingredients) for each selected recipe
        recipes_out = fetch_recipe_details(service.provider, solver_result.recipes, logger)

        return {
            "recipes": recipes_out,
            "generated_at": now().isoformat(),
            "requested_count": solver_result.requested_count,
            "constraint_count": solver_result.constraint_count,
            "status": solver_result.status,
            "warnings": solver_result.warnings,
            "relaxed_constraints": [
                {
                    "label": rc.label,
                    "slack_value": rc.slack_value,
                    "weight": rc.weight,
                    "operator": rc.operator,
                    "original_count": rc.original_count,
                }
                for rc in solver_result.relaxed_constraints
            ],
        }

    async def wait_for_completion(self, timeout: float = 300.0) -> GenerationStatus:
        """Wait for an in-flight generation to finish. Returns final status."""
        if self._current_task and not self._current_task.done():
            await asyncio.wait_for(asyncio.shield(self._current_task), timeout)
        return self._status

    async def shutdown(self, timeout: float = GENERATION_SHUTDOWN_TIMEOUT) -> None:
        """Cancel any in-flight generation task and wait for it to finish."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(self._current_task), timeout=timeout)
            self._status.state = GenerationState.IDLE

    def _cleanup_stale_temp_files(self) -> None:
        """Remove .tmp files left behind by a previous crash."""
        if not os.path.isdir(self.data_dir):
            return
        for fname in os.listdir(self.data_dir):
            if fname.endswith(".tmp"):
                with contextlib.suppress(OSError):
                    os.unlink(os.path.join(self.data_dir, fname))

    def swap_recipe(
        self,
        old_recipe_id: int,
        config: Dict[str, Any],
        url: str,
        token: str,
        logger: Logger,
    ) -> Dict[str, Any]:
        """Replace one recipe in the current menu by re-solving with locked recipes.

        Returns the new recipe dict (with full details). Raises RuntimeError if
        no menu exists, the recipe is not found, or no replacement is available.
        """
        menu = self._cached_menu
        if menu is None:
            raise RuntimeError("No menu to swap from")

        old_index = None
        for i, r in enumerate(menu["recipes"]):
            if r["id"] == old_recipe_id:
                old_index = i
                break
        if old_index is None:
            raise RuntimeError(f"Recipe {old_recipe_id} not in current menu")

        # Build provider and load recipe pool
        cache = int(config.get("cache", API_CACHE_TTL_MINUTES))
        api = TandoorAPI(url, token, logger, cache=cache)
        provider = TandoorProvider(api)
        service = MenuService(config=config, logger=logger, provider=provider)
        service.prepare_data()

        # Lock all current recipes except the one being swapped
        locked_ids = {r["id"] for r in menu["recipes"] if r["id"] != old_recipe_id}
        locked_recipes = [r for r in service.recipes if r.id in locked_ids]

        # Remove the old recipe from the pool so it can't be re-selected
        service.recipes = [r for r in service.recipes if r.id != old_recipe_id]
        service._recipe_set = frozenset(service.recipes)

        if len(service.recipes) < len(locked_recipes) + 1:
            raise RuntimeError("No replacement recipes available in pool")

        # Solve with locked recipes for total = locked + 1
        picker = RecipePicker(
            service.recipes,
            len(locked_recipes) + 1,
            logger=logger,
            locked=locked_recipes,
        )
        service.recipe_picker = picker

        # Apply constraints from the profile
        handlers = {
            "keyword": service._apply_keyword_constraint,
            "food": service._apply_food_constraint,
            "book": service._apply_book_constraint,
            "rating": service._apply_rating_constraint,
            "makenow": service._apply_makenow_constraint,
        }
        for c in service.constraints:
            ctype = c.get("type")
            exclude = c.get("exclude", False)
            soft = c.get("soft", False)
            weight = int(c.get("weight", DEFAULT_SOFT_WEIGHT)) if soft else int(c.get("weight", 0))

            if ctype in handlers:
                handlers[ctype](c, exclude, weight)
            elif ctype in ("cookedon", "createdon"):
                service._apply_date_constraint(c, ctype, exclude, weight)

        try:
            result = picker.solve()
        except RuntimeError:
            raise RuntimeError("No valid replacement found that satisfies constraints") from None

        # Find the new recipe (the one not in locked_ids)
        new_recipe = None
        for r in result.recipes:
            if r.id not in locked_ids:
                new_recipe = r
                break

        if new_recipe is None:
            raise RuntimeError("Solver did not select a new recipe")

        # Fetch full details for the new recipe
        new_details = fetch_recipe_details(provider, [new_recipe], logger)
        if not new_details:
            raise RuntimeError("Failed to fetch details for replacement recipe")

        # Replace in menu and save
        menu["recipes"][old_index] = new_details[0]
        # Update the existing menu row in DB rather than creating a new one
        db_id = menu.get("_db_id")
        if db_id:
            self._menu_repo.update_recipes(db_id, menu["recipes"])
            self._cached_menu = menu
            self._notify_subscribers({"type": "menu_updated", "clear_others": False})
        else:
            self._save_menu(menu)

        return new_details[0]

    def _save_menu(self, menu_data: Dict[str, Any], *, clear_others: bool = False) -> None:
        """Save menu to database and update in-memory cache."""
        menu_data["clear_others"] = clear_others
        profile_name = menu_data.get("profile", "default")
        recipes = menu_data.get("recipes", [])
        generated_at = menu_data.get("generated_at", now().isoformat())

        # Store the full menu dict as metadata for round-trip fidelity
        db_id = self._menu_repo.save_current(
            self._user_id,
            profile_name=profile_name,
            recipes=recipes,
            generated_at=generated_at,
            metadata=menu_data,
        )
        menu_data["_db_id"] = db_id
        self._cached_menu = menu_data
        self._notify_subscribers({"type": "menu_updated", "clear_others": clear_others})
