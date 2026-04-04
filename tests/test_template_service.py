"""Tests for TemplateService — CRUD, validation, expansion, generation plan."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from morsl.services.template_service import TemplateService


@pytest.fixture
def template_service(tmp_path):
    return TemplateService(data_dir=str(tmp_path))


def _make_template(profile="dinner", days=None, meal_type_id=1, recipes_per_day=2):
    return {
        "slots": [
            {
                "days": days or ["mon", "wed", "fri"],
                "profile": profile,
                "meal_type_id": meal_type_id,
                "meal_type_name": "Dinner",
                "recipes_per_day": recipes_per_day,
            }
        ],
        "deduplicate": True,
    }


class TestTemplateNameValidation:
    @pytest.mark.parametrize(
        "name",
        ["valid-name", "a1", "test-123", "weeknight"],
    )
    def test_valid_names_accepted(self, name):
        TemplateService._validate_name(name)  # should not raise

    @pytest.mark.parametrize(
        ("name", "reason"),
        [
            ("", "empty"),
            ("../etc/passwd", "path traversal"),
            ("UPPERCASE", "uppercase"),
            ("-leading-dash", "leading dash"),
            ("has spaces", "spaces"),
            ("has.dot", "dot"),
        ],
    )
    def test_invalid_names_rejected(self, name, reason):
        with pytest.raises(ValueError, match="Invalid template name"):
            TemplateService._validate_name(name)


class TestTemplateCRUD:
    def test_list_empty(self, template_service):
        assert template_service.list_templates() == []

    def test_create_and_get(self, template_service):
        tpl = _make_template()
        created = template_service.create_template("weeknight", tpl)
        assert created["name"] == "weeknight"

        loaded = template_service.get_template("weeknight")
        assert loaded["name"] == "weeknight"
        assert len(loaded["slots"]) == 1

    def test_create_duplicate_raises(self, template_service):
        template_service.create_template("weeknight", _make_template())
        with pytest.raises(FileExistsError, match="already exists"):
            template_service.create_template("weeknight", _make_template())

    def test_list_returns_summaries(self, template_service):
        template_service.create_template("a-template", _make_template())
        template_service.create_template("b-template", _make_template(days=["tue"]))
        result = template_service.list_templates()
        assert len(result) == 2
        names = {t["name"] for t in result}
        assert names == {"a-template", "b-template"}
        assert all("slot_count" in t for t in result)

    def test_update_template(self, template_service):
        template_service.create_template("weeknight", _make_template())
        updated = template_service.update_template("weeknight", _make_template(recipes_per_day=5))
        assert updated["slots"][0]["recipes_per_day"] == 5

    def test_update_nonexistent_raises(self, template_service):
        with pytest.raises(FileNotFoundError, match="not found"):
            template_service.update_template("nope", _make_template())

    def test_delete_template(self, template_service):
        template_service.create_template("weeknight", _make_template())
        template_service.delete_template("weeknight")
        assert template_service.list_templates() == []

    def test_delete_nonexistent_raises(self, template_service):
        with pytest.raises(FileNotFoundError, match="not found"):
            template_service.delete_template("nope")

    def test_get_nonexistent_raises(self, template_service):
        with pytest.raises(FileNotFoundError, match="not found"):
            template_service.get_template("nope")


class TestTemplateValidation:
    def _mock_config_service(self, profile_names):
        cs = MagicMock()
        profiles = [MagicMock(name=n) for n in profile_names]
        # MagicMock overrides 'name', so set it explicitly
        for p, n in zip(profiles, profile_names, strict=True):
            p.name = n
        cs.list_profiles.return_value = profiles
        return cs

    def test_valid_template_no_errors(self, template_service):
        cs = self._mock_config_service(["dinner"])
        errors = template_service.validate_template(_make_template(), cs)
        assert errors == []

    def test_missing_slots(self, template_service):
        cs = self._mock_config_service([])
        errors = template_service.validate_template({}, cs)
        assert any("at least one slot" in e for e in errors)

    def test_invalid_day(self, template_service):
        cs = self._mock_config_service(["dinner"])
        tpl = _make_template(days=["monday"])
        errors = template_service.validate_template(tpl, cs)
        assert any("invalid day" in e for e in errors)

    def test_missing_profile(self, template_service):
        cs = self._mock_config_service(["other"])
        errors = template_service.validate_template(_make_template(), cs)
        assert any("not found" in e for e in errors)

    def test_invalid_recipes_per_day(self, template_service):
        cs = self._mock_config_service(["dinner"])
        tpl = _make_template(recipes_per_day=0)
        errors = template_service.validate_template(tpl, cs)
        assert any("recipes_per_day" in e for e in errors)


class TestExpandSlots:
    def test_expands_days_to_dates(self, template_service):
        tpl = _make_template(days=["mon", "wed"])
        # 2024-01-01 is a Monday
        result = template_service.expand_slots(tpl, date(2024, 1, 1))
        assert "2024-01-01" in result  # Monday
        assert "2024-01-03" in result  # Wednesday
        assert len(result) == 2

    def test_non_monday_raises(self, template_service):
        tpl = _make_template()
        with pytest.raises(ValueError, match="Monday"):
            template_service.expand_slots(tpl, date(2024, 1, 2))  # Tuesday

    def test_assignment_has_correct_fields(self, template_service):
        tpl = _make_template(days=["mon"], meal_type_id=5, recipes_per_day=3)
        result = template_service.expand_slots(tpl, date(2024, 1, 1))
        assignment = result["2024-01-01"][0]
        assert assignment["meal_type_id"] == 5
        assert assignment["recipes_per_day"] == 3
        assert assignment["profile"] == "dinner"


class TestGenerationPlan:
    def test_single_profile(self, template_service):
        tpl = _make_template(days=["mon", "wed", "fri"], recipes_per_day=2)
        plan = template_service.get_generation_plan(tpl)
        assert plan == {"dinner": 6}  # 3 days * 2 rpd

    def test_multiple_profiles(self, template_service):
        tpl = {
            "slots": [
                {
                    "days": ["mon", "tue"],
                    "profile": "dinner",
                    "meal_type_id": 1,
                    "recipes_per_day": 2,
                },
                {
                    "days": ["mon", "tue", "wed"],
                    "profile": "lunch",
                    "meal_type_id": 2,
                    "recipes_per_day": 1,
                },
            ]
        }
        plan = template_service.get_generation_plan(tpl)
        assert plan == {"dinner": 4, "lunch": 3}
