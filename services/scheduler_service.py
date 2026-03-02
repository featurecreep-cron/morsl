from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils import atomic_write_json, now


class SchedulerService:
    """Manages scheduled menu generation using APScheduler."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._scheduler = AsyncIOScheduler()
        self._generation_callback: Optional[Callable[..., Any]] = None
        self._clear_callback: Optional[Callable[[], None]] = None
        self._meal_plan_callback: Optional[Callable[..., Any]] = None
        self._weekly_generation_callback: Optional[Callable[..., Any]] = None
        self._weekly_save_callback: Optional[Callable[..., Any]] = None
        self._load()

    def set_generation_callback(self, callback: Callable[..., Any]) -> None:
        """Set the async callback for triggering generation."""
        self._generation_callback = callback

    def set_clear_callback(self, callback: Callable[[], None]) -> None:
        """Set callback that clears current menu before generation."""
        self._clear_callback = callback

    def set_meal_plan_callback(self, callback: Callable[..., Any]) -> None:
        """Set async callback for meal plan operations (cleanup/create)."""
        self._meal_plan_callback = callback

    def set_weekly_generation_callback(self, callback: Callable[..., Any]) -> None:
        """Set async callback for weekly template generation."""
        self._weekly_generation_callback = callback

    def set_weekly_save_callback(self, callback: Callable[..., Any]) -> None:
        """Set async callback for saving weekly plans to Tandoor."""
        self._weekly_save_callback = callback

    def start(self) -> None:
        """Start the scheduler and restore persisted jobs."""
        for schedule_id, schedule in self._schedules.items():
            if schedule.get("enabled", True):
                self._add_job(schedule_id, schedule)
        self._scheduler.start()

    @property
    def is_running(self) -> bool:
        """Whether the APScheduler event loop is active."""
        return self._scheduler.running

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def create_schedule(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new schedule.

        Exactly one of 'profile' or 'template' must be provided.
        """
        profile = config.get("profile")
        template = config.get("template")
        if not profile and not template:
            raise ValueError("Either 'profile' or 'template' must be provided")
        if profile and template:
            raise ValueError("Cannot set both 'profile' and 'template'")

        schedule_id = str(uuid4())
        schedule = {
            "id": schedule_id,
            "profile": profile,
            "template": template,
            "day_of_week": config.get("day_of_week", "mon-fri"),
            "hour": config.get("hour", 16),
            "minute": config.get("minute", 0),
            "enabled": config.get("enabled", True),
            "clear_before_generate": config.get("clear_before_generate", False),
            "create_meal_plan": config.get("create_meal_plan", False),
            "meal_plan_type": config.get("meal_plan_type"),
            "cleanup_uncooked_days": config.get("cleanup_uncooked_days", 0),
            "last_run": None,
        }
        self._schedules[schedule_id] = schedule
        if schedule["enabled"]:
            self._add_job(schedule_id, schedule)
        self._save()
        return schedule

    def update_schedule(self, schedule_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing schedule."""
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule not found: {schedule_id}")

        schedule = self._schedules[schedule_id]

        # Validate on a copy before mutating the live schedule
        candidate = dict(schedule)
        for key in ("profile", "template", "day_of_week", "hour", "minute", "enabled", "clear_before_generate", "create_meal_plan", "meal_plan_type", "cleanup_uncooked_days"):
            if key in config:
                candidate[key] = config[key]

        if candidate.get("profile") and candidate.get("template"):
            raise ValueError("Cannot set both 'profile' and 'template'")
        if not candidate.get("profile") and not candidate.get("template"):
            raise ValueError("Either 'profile' or 'template' must be provided")

        # Apply validated updates
        schedule.update(candidate)

        # Remove and re-add job
        self._remove_job(schedule_id)
        if schedule["enabled"]:
            self._add_job(schedule_id, schedule)
        self._save()
        return schedule

    def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule not found: {schedule_id}")
        self._remove_job(schedule_id)
        del self._schedules[schedule_id]
        self._save()

    def list_schedules(self) -> List[Dict[str, Any]]:
        """Return all schedules."""
        return list(self._schedules.values())

    def _add_job(self, schedule_id: str, schedule: Dict[str, Any]) -> None:
        """Add a cron job to the scheduler."""
        trigger = CronTrigger(
            day_of_week=schedule["day_of_week"],
            hour=schedule["hour"],
            minute=schedule["minute"],
        )
        self._scheduler.add_job(
            self._run_scheduled_generation,
            trigger=trigger,
            id=schedule_id,
            args=[schedule_id],
            replace_existing=True,
        )

    def _remove_job(self, schedule_id: str) -> None:
        """Remove a job from the scheduler if it exists."""
        try:
            self._scheduler.remove_job(schedule_id)
        except (KeyError, JobLookupError):
            pass

    async def _run_scheduled_generation(self, schedule_id: str) -> None:
        """Pipeline: clear → cleanup uncooked → generate → wait → create meal plans."""
        _logger = logging.getLogger(__name__)
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return

        template_name = schedule.get("template")
        is_weekly = bool(template_name)

        if is_weekly and not self._weekly_generation_callback:
            return
        if not is_weekly and not self._generation_callback:
            return

        # Step 1: Clear menu before generating if configured (profile mode only)
        if not is_weekly and schedule.get("clear_before_generate") and self._clear_callback:
            self._clear_callback()

        # Step 2: Cleanup uncooked meal plans from prior days
        cleanup_days = schedule.get("cleanup_uncooked_days", 0)
        mp_type = schedule.get("meal_plan_type")
        if cleanup_days > 0 and mp_type and self._meal_plan_callback:
            try:
                await self._meal_plan_callback(
                    "cleanup",
                    {
                        "meal_plan_type": mp_type,
                        "cleanup_days": cleanup_days,
                    },
                )
            except Exception as e:
                _logger.warning(f"Scheduled cleanup failed (non-fatal): {e}")

        # Step 3: Generate
        schedule["last_run"] = now().isoformat()
        self._save()

        if is_weekly:
            # Compute week_start as next Monday from now
            from datetime import date, timedelta

            today = date.today()
            days_ahead = 7 - today.weekday()  # next Monday
            if days_ahead == 7:
                days_ahead = 0  # today is Monday
            week_start = today + timedelta(days=days_ahead)
            await self._weekly_generation_callback(template_name, week_start)

            # Step 4: Save weekly plan to Tandoor if configured
            if schedule.get("create_meal_plan") and self._weekly_save_callback:
                try:
                    await self._weekly_save_callback(template_name)
                except Exception as e:
                    _logger.warning(f"Scheduled weekly save failed (non-fatal): {e}")
        else:
            await self._generation_callback(schedule["profile"])

            # Step 4: Create meal plans from generated menu (profile mode)
            if schedule.get("create_meal_plan") and mp_type and self._meal_plan_callback:
                try:
                    await self._meal_plan_callback(
                        "create",
                        {
                            "meal_plan_type": mp_type,
                        },
                    )
                except Exception as e:
                    _logger.warning(f"Scheduled meal plan creation failed (non-fatal): {e}")

    def _save(self) -> None:
        path = os.path.join(self.data_dir, "schedules.json")
        atomic_write_json(path, self._schedules)

    def _load(self) -> None:
        path = os.path.join(self.data_dir, "schedules.json")
        if os.path.isfile(path):
            with open(path) as f:
                self._schedules = json.load(f)
