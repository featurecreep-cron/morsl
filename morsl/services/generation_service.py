from __future__ import annotations

import asyncio
import contextlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from logging import Logger
from typing import Any, Dict, List, Optional
from uuid import uuid4

from morsl.constants import GENERATION_SHUTDOWN_TIMEOUT
from morsl.services.history_service import HistoryService
from morsl.services.menu_service import MenuService
from morsl.services.recipe_detail_service import fetch_recipe_details
from morsl.utils import atomic_write_json, now


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


class GenerationService:
    """Manages asynchronous menu generation with state tracking."""

    def __init__(
        self, data_dir: str = "data", history_service: Optional[HistoryService] = None
    ) -> None:
        self.data_dir = data_dir
        self._history_service = history_service
        self._status = GenerationStatus()
        self._current_task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._cached_menu: Optional[Dict[str, Any]] = None
        self._cleanup_stale_temp_files()
        # Load menu into cache on startup
        self._cached_menu = self._load_menu_from_disk()

    def get_status(self) -> GenerationStatus:
        return self._status

    def get_current_menu(self) -> Optional[Dict[str, Any]]:
        """Return cached menu (loaded from disk on startup, updated on save/clear)."""
        return self._cached_menu

    def _load_menu_from_disk(self) -> Optional[Dict[str, Any]]:
        """Load current menu from disk."""
        menu_path = os.path.join(self.data_dir, "current_menu.json")
        if not os.path.isfile(menu_path):
            return None
        with open(menu_path) as f:
            return json.load(f)

    def clear_menu(self) -> bool:
        """Delete current_menu.json. Returns True if a file was removed."""
        self._cached_menu = None
        menu_path = os.path.join(self.data_dir, "current_menu.json")
        if os.path.isfile(menu_path):
            os.unlink(menu_path)
            return True
        return False

    async def start_generation(
        self,
        config: Dict[str, Any],
        url: str,
        token: str,
        logger: Logger,
        profile_name: str = "default",
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

            loop = asyncio.get_running_loop()
            self._current_task = loop.create_task(
                self._run_generation(config, url, token, logger, request_id, profile_name)
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
    ) -> None:
        """Run the solver in a thread pool and save results."""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._sync_generate, config, url, token, logger
            )

            result["profile"] = profile_name

            # Save to disk atomically
            self._save_menu(result)

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

        except Exception as e:
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
        service = MenuService(url=url, token=token, config=config, logger=logger)
        service.prepare_data()

        if len(service.recipes) < service.choices:
            raise RuntimeError(
                f"Not enough recipes: {len(service.recipes)} available, "
                f"{service.choices} requested"
            )

        solver_result = service.select_recipes()

        # Fetch full details (image + ingredients) for each selected recipe
        recipes_out = fetch_recipe_details(service.tandoor, solver_result.recipes, logger)

        return {
            "recipes": recipes_out,
            "generated_at": now().isoformat(),
            "requested_count": solver_result.requested_count,
            "constraint_count": solver_result.constraint_count,
            "status": solver_result.status,
            "warnings": solver_result.warnings,
            "relaxed_constraints": [
                {"label": rc.label, "slack_value": rc.slack_value, "weight": rc.weight}
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

    def _save_menu(self, menu_data: Dict[str, Any]) -> None:
        """Atomic write and update in-memory cache."""
        menu_path = os.path.join(self.data_dir, "current_menu.json")
        atomic_write_json(menu_path, menu_data)
        self._cached_menu = menu_data
