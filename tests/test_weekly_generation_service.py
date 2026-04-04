"""Tests for WeeklyGenerationService — plan CRUD, validation, state machine."""

from __future__ import annotations

import os

import pytest

from morsl.services.generation_service import GenerationState
from morsl.services.weekly_generation_service import (
    WeeklyGenerationService,
    _distribute_to_slots,
    _validate_template_name,
)


@pytest.fixture
def weekly_service(tmp_path):
    return WeeklyGenerationService(data_dir=str(tmp_path))


class TestTemplateNameValidation:
    @pytest.mark.parametrize("name", ["weeknight", "a1", "test-plan"])
    def test_valid_names(self, name):
        _validate_template_name(name)  # no raise

    @pytest.mark.parametrize("name", ["", "../escape", "UPPER", "-dash"])
    def test_invalid_names(self, name):
        with pytest.raises(ValueError, match="Invalid template name"):
            _validate_template_name(name)


class TestPlanCRUD:
    def test_get_plan_none_when_missing(self, weekly_service):
        assert weekly_service.get_plan("weeknight") is None

    def test_save_and_get_plan(self, weekly_service):
        plan = {"template": "weeknight", "days": {}, "warnings": []}
        weekly_service._save_plan("weeknight", plan)
        loaded = weekly_service.get_plan("weeknight")
        assert loaded["template"] == "weeknight"

    def test_save_creates_directory(self, weekly_service):
        weekly_service._save_plan("weeknight", {"template": "weeknight"})
        assert os.path.isdir(weekly_service.plans_dir)

    def test_clear_plan_removes_file(self, weekly_service):
        weekly_service._save_plan("weeknight", {"template": "weeknight"})
        assert weekly_service.clear_plan("weeknight") is True
        assert weekly_service.get_plan("weeknight") is None

    def test_clear_plan_returns_false_when_missing(self, weekly_service):
        assert weekly_service.clear_plan("weeknight") is False

    def test_get_plan_handles_corrupt_json(self, weekly_service, tmp_path):
        os.makedirs(weekly_service.plans_dir, exist_ok=True)
        plan_path = os.path.join(weekly_service.plans_dir, "weeknight.json")
        with open(plan_path, "w") as f:
            f.write("{invalid json")
        assert weekly_service.get_plan("weeknight") is None


class TestWeeklyStateTransitions:
    def test_initial_state_idle(self, weekly_service):
        assert weekly_service.get_status().state == GenerationState.IDLE

    @pytest.mark.asyncio
    async def test_shutdown_when_idle(self, weekly_service):
        await weekly_service.shutdown()  # should not raise
        assert weekly_service.get_status().state == GenerationState.IDLE


class TestDistributeToSlots:
    def test_distributes_recipes_to_correct_days(self):
        from morsl.models import make_recipe as _mr

        _base = {
            "keywords": [],
            "rating": 0,
            "new": False,
            "servings": 4,
            "created_at": "2024-01-01T00:00:00",
        }
        r1 = _mr({"id": 1, "name": "A", **_base})
        r2 = _mr({"id": 2, "name": "B", **_base})

        _slot = {
            "meal_type_id": 1,
            "meal_type_name": "Dinner",
            "profile": "dinner",
            "recipes_per_day": 1,
        }
        expanded = {
            "2024-01-01": [_slot],
            "2024-01-02": [_slot],
        }
        profile_recipes = {"dinner": [r1, r2]}
        detail_map = {
            1: {"id": 1, "name": "A", "image": None},
            2: {"id": 2, "name": "B", "image": None},
        }

        result = _distribute_to_slots(expanded, profile_recipes, detail_map)
        assert "2024-01-01" in result
        assert "2024-01-02" in result
        day1_recipes = result["2024-01-01"]["meals"]["1"]["recipes"]
        day2_recipes = result["2024-01-02"]["meals"]["1"]["recipes"]
        assert len(day1_recipes) == 1
        assert len(day2_recipes) == 1
        # Recipes are distributed in order — first to day 1, second to day 2
        assert day1_recipes[0]["id"] == 1
        assert day2_recipes[0]["id"] == 2

    def test_empty_queue_produces_empty_recipes(self):
        slot = {
            "meal_type_id": 1,
            "meal_type_name": "Dinner",
            "profile": "dinner",
            "recipes_per_day": 2,
        }
        expanded = {"2024-01-01": [slot]}
        result = _distribute_to_slots(expanded, {}, {})
        assert result["2024-01-01"]["meals"]["1"]["recipes"] == []
