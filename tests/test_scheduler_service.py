from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from morsl.services.scheduler_service import SchedulerService


@pytest.fixture
def scheduler_service(tmp_path):
    svc = SchedulerService(data_dir=str(tmp_path))
    return svc


class TestSchedulerService:
    def test_init_empty(self, scheduler_service):
        assert scheduler_service._schedules == {}
        assert scheduler_service._generation_callback is None

    def test_create_schedule(self, scheduler_service):
        schedule = scheduler_service.create_schedule(
            {
                "profile": "gin",
                "day_of_week": "mon-fri",
                "hour": 16,
                "minute": 30,
            }
        )
        assert schedule["profile"] == "gin"
        assert schedule["day_of_week"] == "mon-fri"
        assert schedule["hour"] == 16
        assert schedule["minute"] == 30
        assert schedule["enabled"] is True
        assert schedule["last_run"] is None
        assert "id" in schedule

    def test_create_schedule_persists(self, scheduler_service, tmp_path):
        scheduler_service.create_schedule({"profile": "tiki"})
        path = tmp_path / "schedules.json"
        assert path.is_file()
        data = json.loads(path.read_text())
        assert len(data) == 1

    def test_list_schedules(self, scheduler_service):
        scheduler_service.create_schedule({"profile": "gin"})
        scheduler_service.create_schedule({"profile": "rum"})
        schedules = scheduler_service.list_schedules()
        assert len(schedules) == 2
        names = {s["profile"] for s in schedules}
        assert names == {"gin", "rum"}

    def test_update_schedule(self, scheduler_service):
        s = scheduler_service.create_schedule({"profile": "gin", "hour": 10})
        updated = scheduler_service.update_schedule(s["id"], {"hour": 18, "minute": 45})
        assert updated["hour"] == 18
        assert updated["minute"] == 45
        assert updated["profile"] == "gin"  # unchanged

    def test_update_schedule_not_found(self, scheduler_service):
        with pytest.raises(KeyError, match="Schedule not found"):
            scheduler_service.update_schedule("nonexistent-id", {"hour": 10})

    def test_delete_schedule(self, scheduler_service):
        s = scheduler_service.create_schedule({"profile": "gin"})
        scheduler_service.delete_schedule(s["id"])
        assert len(scheduler_service.list_schedules()) == 0

    def test_delete_schedule_not_found(self, scheduler_service):
        with pytest.raises(KeyError, match="Schedule not found"):
            scheduler_service.delete_schedule("nonexistent-id")

    def test_disable_enable_schedule(self, scheduler_service):
        s = scheduler_service.create_schedule({"profile": "gin", "enabled": True})
        updated = scheduler_service.update_schedule(s["id"], {"enabled": False})
        assert updated["enabled"] is False
        updated = scheduler_service.update_schedule(s["id"], {"enabled": True})
        assert updated["enabled"] is True

    def test_load_persisted_schedules(self, tmp_path):
        # Create a schedule, then create a new service pointing to same dir
        svc1 = SchedulerService(data_dir=str(tmp_path))
        svc1.create_schedule({"profile": "whiskey", "hour": 9})

        svc2 = SchedulerService(data_dir=str(tmp_path))
        schedules = svc2.list_schedules()
        assert len(schedules) == 1
        assert schedules[0]["profile"] == "whiskey"

    def test_set_generation_callback(self, scheduler_service):
        callback = AsyncMock()
        scheduler_service.set_generation_callback(callback)
        assert scheduler_service._generation_callback is callback

    def test_create_schedule_defaults(self, scheduler_service):
        schedule = scheduler_service.create_schedule({"profile": "default"})
        assert schedule["day_of_week"] == "mon-fri"
        assert schedule["hour"] == 16
        assert schedule["minute"] == 0

    @pytest.mark.asyncio
    async def test_start_stop(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        svc.start()
        assert svc._scheduler.running
        svc.stop()
        # shutdown(wait=False) may still report running briefly; verify it doesn't raise
        # The important thing is that stop() doesn't error

    @pytest.mark.asyncio
    async def test_start_with_disabled_schedule(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        svc.create_schedule({"profile": "gin", "enabled": False})
        svc.start()
        # Disabled schedule should not be added as a job
        jobs = svc._scheduler.get_jobs()
        assert len(jobs) == 0
        svc.stop()

    @pytest.mark.asyncio
    async def test_start_with_enabled_schedule(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        svc.create_schedule({"profile": "gin", "enabled": True})
        svc.start()
        jobs = svc._scheduler.get_jobs()
        assert len(jobs) == 1
        svc.stop()

    @pytest.mark.asyncio
    async def test_clear_before_generate_passes_flag(self, tmp_path):
        """clear_before_generate passes clear_others=True to the generation callback.

        The menu is not cleared before generation (avoids data loss on failure).
        Instead, the flag is forwarded so the generated menu includes clear_others,
        telling the frontend to wipe stale shelves after successful generation.
        """
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)

        schedule = svc.create_schedule(
            {"profile": "gin", "clear_before_generate": True, "enabled": True}
        )
        await svc._run_scheduled_generation(schedule["id"])

        gen_mock.assert_called_once_with("gin", clear_others=True)

    @pytest.mark.asyncio
    async def test_clear_before_generate_false_omits_flag(self, tmp_path):
        """When clear_before_generate is false, clear_others=False is passed."""
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)

        schedule = svc.create_schedule(
            {"profile": "gin", "clear_before_generate": False, "enabled": True}
        )
        await svc._run_scheduled_generation(schedule["id"])

        gen_mock.assert_called_once_with("gin", clear_others=False)

    @pytest.mark.asyncio
    async def test_profile_pipeline_creates_meal_plan(self, tmp_path):
        """When create_meal_plan is set, meal plan callback fires after generation."""
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        mp_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)
        svc.set_meal_plan_callback(mp_mock)

        schedule = svc.create_schedule(
            {
                "profile": "gin",
                "create_meal_plan": True,
                "meal_plan_type": 3,
                "enabled": True,
            }
        )
        await svc._run_scheduled_generation(schedule["id"])

        gen_mock.assert_called_once()
        mp_mock.assert_called_once_with("create", {"meal_plan_type": 3})

    @pytest.mark.asyncio
    async def test_profile_pipeline_skips_meal_plan_when_disabled(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        mp_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)
        svc.set_meal_plan_callback(mp_mock)

        schedule = svc.create_schedule(
            {"profile": "gin", "create_meal_plan": False, "enabled": True}
        )
        await svc._run_scheduled_generation(schedule["id"])

        gen_mock.assert_called_once()
        mp_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_generate_cleanup(self, tmp_path):
        """cleanup_uncooked_days triggers meal plan cleanup before generation."""
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        mp_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)
        svc.set_meal_plan_callback(mp_mock)

        schedule = svc.create_schedule(
            {
                "profile": "gin",
                "cleanup_uncooked_days": 7,
                "meal_plan_type": 3,
                "enabled": True,
            }
        )
        await svc._run_scheduled_generation(schedule["id"])

        # Cleanup call should happen before generation
        assert mp_mock.call_count == 1
        mp_mock.assert_called_once_with("cleanup", {"meal_plan_type": 3, "cleanup_days": 7})

    @pytest.mark.asyncio
    async def test_weekly_pipeline_calls_weekly_callback(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        weekly_mock = AsyncMock()
        svc.set_weekly_generation_callback(weekly_mock)

        schedule = svc.create_schedule({"template": "weeknight", "enabled": True})
        await svc._run_scheduled_generation(schedule["id"])

        weekly_mock.assert_called_once()
        call_args = weekly_mock.call_args
        assert call_args[0][0] == "weeknight"

    @pytest.mark.asyncio
    async def test_scheduled_generation_updates_last_run(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)

        schedule = svc.create_schedule({"profile": "gin", "enabled": True})
        assert schedule["last_run"] is None

        await svc._run_scheduled_generation(schedule["id"])

        updated = svc._schedules[schedule["id"]]
        assert updated["last_run"] is not None

    @pytest.mark.asyncio
    async def test_missing_schedule_id_returns_early(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        gen_mock = AsyncMock()
        svc.set_generation_callback(gen_mock)
        await svc._run_scheduled_generation("nonexistent-id")
        gen_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_callback_returns_early(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        # No callback set
        schedule = svc.create_schedule({"profile": "gin", "enabled": True})
        await svc._run_scheduled_generation(schedule["id"])
        # Should complete without error

    def test_create_requires_profile_or_template(self, scheduler_service):
        with pytest.raises(ValueError, match="Either"):
            scheduler_service.create_schedule({})

    def test_create_rejects_both_profile_and_template(self, scheduler_service):
        with pytest.raises(ValueError, match="Cannot set both"):
            scheduler_service.create_schedule({"profile": "gin", "template": "weeknight"})

    def test_update_rejects_both_profile_and_template(self, scheduler_service):
        s = scheduler_service.create_schedule({"profile": "gin"})
        with pytest.raises(ValueError, match="Cannot set both"):
            scheduler_service.update_schedule(s["id"], {"template": "weeknight"})
