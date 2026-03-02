from __future__ import annotations

import json
import os

import pytest

from services.category_service import CategoryService


class TestCategoryServiceCRUD:
    def test_first_load_creates_empty_file(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        assert svc.list_categories() == []
        assert os.path.isfile(tmp_path / "categories.json")

    def test_load_existing_file(self, tmp_path):
        cats = {"spirits": {"id": "spirits", "display_name": "Spirits", "subtitle": "", "icon": "", "sort_order": 0}}
        (tmp_path / "categories.json").write_text(json.dumps(cats))
        svc = CategoryService(data_dir=str(tmp_path))
        assert len(svc.list_categories()) == 1
        assert svc.list_categories()[0]["id"] == "spirits"

    def test_create_category(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        cat = svc.create_category({"display_name": "By Spirit", "subtitle": "Whiskey, Gin...", "icon": "bowl"})
        assert cat["id"] == "by-spirit"
        assert cat["display_name"] == "By Spirit"
        assert cat["subtitle"] == "Whiskey, Gin..."
        assert cat["icon"] == "bowl"
        assert cat["sort_order"] == 0

    def test_create_auto_increments_sort_order(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        first = svc.create_category({"display_name": "First"})
        second = svc.create_category({"display_name": "Second"})
        assert first["sort_order"] == 0
        assert second["sort_order"] == 1

    def test_create_deduplicates_id(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "By Spirit"})
        dup = svc.create_category({"display_name": "By Spirit"})
        assert dup["id"] == "by-spirit-2"

    def test_create_with_explicit_id(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        cat = svc.create_category({"id": "custom-id", "display_name": "Custom"})
        assert cat["id"] == "custom-id"

    def test_update_category(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "Old Name"})
        updated = svc.update_category("old-name", {"display_name": "New Name", "subtitle": "Updated"})
        assert updated["display_name"] == "New Name"
        assert updated["subtitle"] == "Updated"

    def test_update_sort_order(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "Test"})
        updated = svc.update_category("test", {"sort_order": 5})
        assert updated["sort_order"] == 5

    def test_update_nonexistent_raises(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        with pytest.raises(KeyError, match="Category not found"):
            svc.update_category("nope", {"display_name": "X"})

    def test_delete_category(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "Doomed"})
        assert len(svc.list_categories()) == 1
        svc.delete_category("doomed")
        assert len(svc.list_categories()) == 0

    def test_delete_nonexistent_raises(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        with pytest.raises(KeyError, match="Category not found"):
            svc.delete_category("nope")

    def test_persistence_across_instances(self, tmp_path):
        svc1 = CategoryService(data_dir=str(tmp_path))
        svc1.create_category({"display_name": "Persistent"})
        svc2 = CategoryService(data_dir=str(tmp_path))
        cats = svc2.list_categories()
        assert len(cats) == 1
        assert cats[0]["display_name"] == "Persistent"


class TestCategoryServiceReorder:
    def test_reorder_categories(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "Alpha"})
        svc.create_category({"display_name": "Beta"})
        svc.create_category({"display_name": "Gamma"})
        result = svc.reorder_categories(["gamma", "alpha", "beta"])
        assert [c["id"] for c in result] == ["gamma", "alpha", "beta"]

    def test_reorder_ignores_unknown_ids(self, tmp_path):
        svc = CategoryService(data_dir=str(tmp_path))
        svc.create_category({"display_name": "Only"})
        result = svc.reorder_categories(["nonexistent", "only"])
        assert len(result) == 1
        assert result[0]["sort_order"] == 1


class TestCategoryServiceMigration:
    def _write_categories(self, tmp_path, cats):
        (tmp_path / "categories.json").write_text(json.dumps(cats))

    def test_migrate_old_cuisine_to_spirit(self, tmp_path):
        self._write_categories(tmp_path, {
            "by-cuisine": {"id": "by-cuisine", "display_name": "By Cuisine", "subtitle": "Italian, Thai...", "icon": "food", "sort_order": 0},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        cats = svc.list_categories()
        assert len(cats) == 1
        assert cats[0]["id"] == "by-spirit"
        assert cats[0]["display_name"] == "By Spirit"
        assert cats[0]["subtitle"] == "Whiskey, Gin, Rum..."

    def test_migrate_old_meal_to_style(self, tmp_path):
        self._write_categories(tmp_path, {
            "by-meal": {"id": "by-meal", "display_name": "By Meal", "subtitle": "Dinner, Lunch...", "icon": "plate", "sort_order": 1},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        cats = svc.list_categories()
        assert cats[0]["id"] == "by-style"
        assert cats[0]["display_name"] == "By Style"
        assert cats[0]["subtitle"] == "Martini, Negroni, Sour..."

    def test_migrate_fixes_display_name_on_already_renamed(self, tmp_path):
        self._write_categories(tmp_path, {
            "by-spirit": {"id": "by-spirit", "display_name": "By Cuisine", "subtitle": "Old subtitle", "icon": "old", "sort_order": 0},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        cat = svc.list_categories()[0]
        assert cat["display_name"] == "By Spirit"
        assert cat["subtitle"] == "Whiskey, Gin, Rum..."

    def test_migrate_skips_if_target_exists(self, tmp_path):
        self._write_categories(tmp_path, {
            "by-cuisine": {"id": "by-cuisine", "display_name": "By Cuisine", "subtitle": "", "icon": "", "sort_order": 0},
            "by-spirit": {"id": "by-spirit", "display_name": "By Spirit", "subtitle": "Already here", "icon": "bowl", "sort_order": 1},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        cats = {c["id"]: c for c in svc.list_categories()}
        assert "by-cuisine" in cats
        assert cats["by-spirit"]["subtitle"] == "Already here"

    def test_migrate_fixes_blank_house_menu_subtitle(self, tmp_path):
        self._write_categories(tmp_path, {
            "house-menu": {"id": "house-menu", "display_name": "House Menu", "subtitle": "", "icon": "", "sort_order": 0},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        cat = svc.list_categories()[0]
        assert cat["subtitle"] == "Random cocktails"

    def test_already_migrated_data_unchanged(self, tmp_path):
        already_migrated = {
            "by-spirit": {"id": "by-spirit", "display_name": "By Spirit", "subtitle": "Whiskey, Gin, Rum...", "icon": "bowl", "sort_order": 0},
            "by-style": {"id": "by-style", "display_name": "By Style", "subtitle": "Martini, Negroni, Sour...", "icon": "dinner", "sort_order": 1},
            "house-menu": {"id": "house-menu", "display_name": "House Menu", "subtitle": "Random cocktails", "icon": "", "sort_order": 2},
        }
        self._write_categories(tmp_path, already_migrated)
        svc = CategoryService(data_dir=str(tmp_path))
        # Re-read from disk to verify no unnecessary write
        with open(tmp_path / "categories.json") as f:
            on_disk = json.load(f)
        assert on_disk == already_migrated

    def test_migrate_both_old_ids_simultaneously(self, tmp_path):
        self._write_categories(tmp_path, {
            "by-cuisine": {"id": "by-cuisine", "display_name": "By Cuisine", "subtitle": "", "icon": "", "sort_order": 0},
            "by-meal": {"id": "by-meal", "display_name": "By Meal", "subtitle": "", "icon": "", "sort_order": 1},
        })
        svc = CategoryService(data_dir=str(tmp_path))
        ids = {c["id"] for c in svc.list_categories()}
        assert ids == {"by-spirit", "by-style"}
