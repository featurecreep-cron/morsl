"""Tests for JSON-to-SQLite migration."""

from __future__ import annotations

import json
import os

import pytest

from morsl.db import get_db
from morsl.migrate_json_to_db import migrate
from morsl.repositories import (
    HistoryRepository,
    MenuRepository,
    ProfileRepository,
    SettingsRepository,
    TemplateRepository,
)


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with sample JSON files."""
    d = str(tmp_path)

    # settings.json
    with open(os.path.join(d, "settings.json"), "w") as f:
        json.dump({"theme": "moss", "app_name": "Test Morsl", "pin": "1234"}, f)

    # profiles
    profiles_dir = os.path.join(d, "profiles")
    os.makedirs(profiles_dir)
    with open(os.path.join(profiles_dir, "dinner.json"), "w") as f:
        json.dump({"choices": 5, "constraints": [], "default": True}, f)
    with open(os.path.join(profiles_dir, "lunch.json"), "w") as f:
        json.dump({"choices": 3, "constraints": []}, f)
    with open(os.path.join(profiles_dir, "base.json"), "w") as f:
        json.dump({"cache": 240}, f)

    # current_menu.json
    with open(os.path.join(d, "current_menu.json"), "w") as f:
        json.dump(
            {
                "recipes": [{"id": 1, "name": "Soup"}, {"id": 2, "name": "Salad"}],
                "generated_at": "2026-04-19T12:00:00",
                "profile": "dinner",
                "status": "optimal",
                "warnings": [],
            },
            f,
        )

    # templates
    templates_dir = os.path.join(d, "templates")
    os.makedirs(templates_dir)
    with open(os.path.join(templates_dir, "weekplan.json"), "w") as f:
        json.dump(
            {
                "name": "weekplan",
                "slots": [{"profile": "dinner", "days": ["mon", "tue"]}],
            },
            f,
        )

    # generation_history.json
    with open(os.path.join(d, "generation_history.json"), "w") as f:
        json.dump(
            [
                {
                    "profile": "dinner",
                    "recipe_count": 5,
                    "duration_ms": 1200,
                    "status": "optimal",
                    "generated_at": "2026-04-19T12:00:00",
                    "relaxed_constraints": [],
                },
                {
                    "profile": "lunch",
                    "recipe_count": 3,
                    "duration_ms": 800,
                    "status": "optimal",
                    "generated_at": "2026-04-18T12:00:00",
                },
            ],
            f,
        )

    return d


class TestMigration:
    def test_migrates_settings(self, data_dir):
        migrate(data_dir)
        conn = get_db(data_dir)
        repo = SettingsRepository(conn)
        assert repo.get(1, "theme") == "moss"
        assert repo.get(1, "app_name") == "Test Morsl"

    def test_migrates_profiles(self, data_dir):
        migrate(data_dir)
        conn = get_db(data_dir)
        repo = ProfileRepository(conn)
        profiles = repo.list_all(1)
        names = {p["name"] for p in profiles}
        assert "dinner" in names
        assert "lunch" in names
        assert "base" in names  # base is stored too

        dinner = repo.get_by_name(1, "dinner")
        assert dinner["is_default"]
        assert dinner["config"]["choices"] == 5

    def test_migrates_menu(self, data_dir):
        migrate(data_dir)
        conn = get_db(data_dir)
        repo = MenuRepository(conn)
        menu = repo.get_current(1)
        assert menu is not None
        assert len(menu["recipes"]) == 2
        assert menu["profile_name"] == "dinner"

    def test_migrates_templates(self, data_dir):
        migrate(data_dir)
        conn = get_db(data_dir)
        repo = TemplateRepository(conn)
        tpl = repo.get_by_name(1, "weekplan")
        assert tpl is not None
        assert len(tpl["config"]["slots"]) == 1

    def test_migrates_history(self, data_dir):
        migrate(data_dir)
        conn = get_db(data_dir)
        repo = HistoryRepository(conn)
        entries, total = repo.list_entries(1)
        assert total == 2
        assert entries[0]["profile_name"] in ("dinner", "lunch")

    def test_idempotent(self, data_dir):
        assert migrate(data_dir) is True
        assert migrate(data_dir) is False  # already migrated

    def test_no_json_files(self, tmp_path):
        """Migration with empty data dir creates user but no data."""
        d = str(tmp_path)
        migrate(d)
        conn = get_db(d)
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        assert row[0] == 1

    def test_json_files_not_deleted(self, data_dir):
        """Migration does not remove the original JSON files."""
        migrate(data_dir)
        assert os.path.isfile(os.path.join(data_dir, "settings.json"))
        assert os.path.isfile(os.path.join(data_dir, "current_menu.json"))
