"""Tests for the database layer and repositories."""

from __future__ import annotations

import os
import sqlite3

import pytest

from morsl.db import (
    SCHEMA_VERSION,
    get_connection,
    json_col,
    parse_json_col,
)
from morsl.repositories import (
    HistoryRepository,
    MenuRepository,
    ProfileRepository,
    SettingsRepository,
    TemplateRepository,
)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory."""
    return str(tmp_path)


@pytest.fixture
def conn(tmp_data_dir):
    """Provide a fresh database connection."""
    c = get_connection(tmp_data_dir)
    yield c
    c.close()


@pytest.fixture
def user_id(conn):
    """Create a test user and return their ID."""
    conn.execute("INSERT INTO users (username, password_hash) VALUES ('test', '')")
    conn.commit()
    return conn.execute("SELECT id FROM users WHERE username = 'test'").fetchone()[0]


# ---------------------------------------------------------------------------
# Database core
# ---------------------------------------------------------------------------


class TestDatabase:
    def test_creates_database_file(self, tmp_data_dir):
        conn = get_connection(tmp_data_dir)
        assert os.path.isfile(os.path.join(tmp_data_dir, "morsl.db"))
        conn.close()

    def test_wal_mode(self, conn):
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_foreign_keys_enabled(self, conn):
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

    def test_schema_version(self, conn):
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == SCHEMA_VERSION

    def test_idempotent_migration(self, tmp_data_dir):
        """Opening a connection twice doesn't re-run migrations."""
        c1 = get_connection(tmp_data_dir)
        c2 = get_connection(tmp_data_dir)
        rows = c2.execute("SELECT COUNT(*) FROM schema_version").fetchone()
        assert rows[0] == SCHEMA_VERSION
        c1.close()
        c2.close()

    def test_tables_exist(self, conn):
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        expected = {
            "schema_version",
            "users",
            "settings",
            "profiles",
            "menus",
            "templates",
            "orders",
            "generation_history",
            "weekly_plans",
        }
        assert expected.issubset(tables)


class TestJsonHelpers:
    def test_json_col_dict(self):
        assert json_col({"a": 1}) == '{"a":1}'

    def test_json_col_list(self):
        assert json_col([1, 2]) == "[1,2]"

    def test_parse_json_col(self):
        assert parse_json_col('{"a":1}') == {"a": 1}

    def test_parse_json_col_none(self):
        assert parse_json_col(None) is None

    def test_parse_json_col_default(self):
        assert parse_json_col(None, []) == []

    def test_parse_json_col_invalid(self):
        assert parse_json_col("not json", {}) == {}


# ---------------------------------------------------------------------------
# Settings repository
# ---------------------------------------------------------------------------


class TestSettingsRepository:
    def test_get_empty(self, conn, user_id):
        repo = SettingsRepository(conn)
        assert repo.get_all(user_id) == {}

    def test_set_and_get(self, conn, user_id):
        repo = SettingsRepository(conn)
        repo.set(user_id, "theme", "dark")
        assert repo.get(user_id, "theme") == "dark"

    def test_set_many(self, conn, user_id):
        repo = SettingsRepository(conn)
        repo.set_many(user_id, {"theme": "dark", "app_name": "Test"})
        all_settings = repo.get_all(user_id)
        assert all_settings["theme"] == "dark"
        assert all_settings["app_name"] == "Test"

    def test_upsert(self, conn, user_id):
        repo = SettingsRepository(conn)
        repo.set(user_id, "theme", "dark")
        repo.set(user_id, "theme", "light")
        assert repo.get(user_id, "theme") == "light"

    def test_delete(self, conn, user_id):
        repo = SettingsRepository(conn)
        repo.set(user_id, "theme", "dark")
        repo.delete(user_id, "theme")
        assert repo.get(user_id, "theme") is None

    def test_stores_complex_values(self, conn, user_id):
        repo = SettingsRepository(conn)
        repo.set(user_id, "complex", {"nested": [1, 2, 3]})
        assert repo.get(user_id, "complex") == {"nested": [1, 2, 3]}

    def test_user_isolation(self, conn):
        conn.execute("INSERT INTO users (username, password_hash) VALUES ('a', '')")
        conn.execute("INSERT INTO users (username, password_hash) VALUES ('b', '')")
        conn.commit()
        uid_a = conn.execute("SELECT id FROM users WHERE username='a'").fetchone()[0]
        uid_b = conn.execute("SELECT id FROM users WHERE username='b'").fetchone()[0]

        repo = SettingsRepository(conn)
        repo.set(uid_a, "theme", "dark")
        repo.set(uid_b, "theme", "light")
        assert repo.get(uid_a, "theme") == "dark"
        assert repo.get(uid_b, "theme") == "light"


# ---------------------------------------------------------------------------
# Profile repository
# ---------------------------------------------------------------------------


class TestProfileRepository:
    def test_create_and_get(self, conn, user_id):
        repo = ProfileRepository(conn)
        config = {"choices": 5, "constraints": []}
        repo.create(user_id, "dinner", config)
        result = repo.get_by_name(user_id, "dinner")
        assert result is not None
        assert result["config"] == config

    def test_list_all(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "breakfast", {"choices": 3})
        repo.create(user_id, "dinner", {"choices": 5})
        profiles = repo.list_all(user_id)
        names = [p["name"] for p in profiles]
        assert names == ["breakfast", "dinner"]

    def test_update(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "dinner", {"choices": 5})
        repo.update(user_id, "dinner", {"choices": 7})
        result = repo.get_by_name(user_id, "dinner")
        assert result["config"]["choices"] == 7

    def test_delete(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "dinner", {"choices": 5})
        assert repo.delete(user_id, "dinner")
        assert repo.get_by_name(user_id, "dinner") is None

    def test_delete_nonexistent(self, conn, user_id):
        repo = ProfileRepository(conn)
        assert not repo.delete(user_id, "nope")

    def test_set_default(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "a", {})
        repo.create(user_id, "b", {})
        repo.set_default(user_id, "b")
        a = repo.get_by_name(user_id, "a")
        b = repo.get_by_name(user_id, "b")
        assert not a["is_default"]
        assert b["is_default"]

    def test_exists(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "dinner", {})
        assert repo.exists(user_id, "dinner")
        assert not repo.exists(user_id, "lunch")

    def test_unique_constraint(self, conn, user_id):
        repo = ProfileRepository(conn)
        repo.create(user_id, "dinner", {})
        with pytest.raises(sqlite3.IntegrityError):
            repo.create(user_id, "dinner", {})


# ---------------------------------------------------------------------------
# Menu repository
# ---------------------------------------------------------------------------


class TestMenuRepository:
    def test_save_and_get_current(self, conn, user_id):
        repo = MenuRepository(conn)
        recipes = [{"id": 1, "name": "Soup"}]
        repo.save_current(user_id, "dinner", recipes, "2026-04-19T12:00:00")
        menu = repo.get_current(user_id)
        assert menu is not None
        assert menu["recipes"] == recipes
        assert menu["profile_name"] == "dinner"

    def test_new_current_replaces_old(self, conn, user_id):
        repo = MenuRepository(conn)
        repo.save_current(user_id, "dinner", [{"id": 1}], "2026-04-19T12:00:00")
        repo.save_current(user_id, "lunch", [{"id": 2}], "2026-04-19T13:00:00")
        menu = repo.get_current(user_id)
        assert menu["profile_name"] == "lunch"
        assert menu["recipes"] == [{"id": 2}]

    def test_clear_current(self, conn, user_id):
        repo = MenuRepository(conn)
        repo.save_current(user_id, "dinner", [{"id": 1}], "2026-04-19T12:00:00")
        repo.clear_current(user_id)
        assert repo.get_current(user_id) is None

    def test_update_recipes(self, conn, user_id):
        repo = MenuRepository(conn)
        repo.save_current(user_id, "dinner", [{"id": 1}], "2026-04-19T12:00:00")
        menu = repo.get_current(user_id)
        repo.update_recipes(menu["id"], [{"id": 2}])
        updated = repo.get_current(user_id)
        assert updated["recipes"] == [{"id": 2}]

    def test_list_recent(self, conn, user_id):
        repo = MenuRepository(conn)
        for i in range(5):
            repo.save_current(user_id, f"profile_{i}", [{"id": i}], f"2026-04-{19 + i}")
        recent = repo.list_recent(user_id, limit=3)
        assert len(recent) == 3
        assert recent[0]["profile_name"] == "profile_4"


# ---------------------------------------------------------------------------
# Template repository
# ---------------------------------------------------------------------------


class TestTemplateRepository:
    def test_create_and_get(self, conn, user_id):
        repo = TemplateRepository(conn)
        config = {"slots": [{"profile": "dinner", "days": ["mon"]}]}
        repo.create(user_id, "weekplan", config)
        result = repo.get_by_name(user_id, "weekplan")
        assert result is not None
        assert result["config"] == config

    def test_list_all(self, conn, user_id):
        repo = TemplateRepository(conn)
        repo.create(user_id, "a-plan", {})
        repo.create(user_id, "b-plan", {})
        templates = repo.list_all(user_id)
        assert len(templates) == 2

    def test_update(self, conn, user_id):
        repo = TemplateRepository(conn)
        repo.create(user_id, "plan", {"slots": []})
        repo.update(user_id, "plan", {"slots": [{"profile": "lunch"}]})
        result = repo.get_by_name(user_id, "plan")
        assert len(result["config"]["slots"]) == 1

    def test_delete(self, conn, user_id):
        repo = TemplateRepository(conn)
        repo.create(user_id, "plan", {})
        assert repo.delete(user_id, "plan")
        assert repo.get_by_name(user_id, "plan") is None


# ---------------------------------------------------------------------------
# History repository
# ---------------------------------------------------------------------------


class TestHistoryRepository:
    def test_add_and_list(self, conn, user_id):
        repo = HistoryRepository(conn)
        repo.add_entry(user_id, "dinner", 5, 1200, "optimal", "2026-04-19T12:00:00")
        entries, total = repo.list_entries(user_id)
        assert total == 1
        assert entries[0]["profile_name"] == "dinner"
        assert entries[0]["recipe_count"] == 5

    def test_pagination(self, conn, user_id):
        repo = HistoryRepository(conn)
        for i in range(10):
            repo.add_entry(user_id, f"p{i}", i, 100, "optimal", f"2026-04-{i + 1}")
        entries, total = repo.list_entries(user_id, limit=3, offset=2)
        assert total == 10
        assert len(entries) == 3

    def test_analytics(self, conn, user_id):
        repo = HistoryRepository(conn)
        for i in range(5):
            metadata = {"relaxed_constraints": [{"label": "test", "slack_value": 0.5}]}
            repo.add_entry(
                user_id, "dinner", 5, 1000 + i * 100, "optimal", f"2026-04-{i + 1}", metadata
            )
        analytics = repo.get_analytics(user_id)
        assert analytics["total_generations"] == 5
        assert analytics["avg_duration_ms"] > 0
        assert len(analytics["most_relaxed"]) == 1
        assert analytics["most_relaxed"][0]["label"] == "test"

    def test_clear(self, conn, user_id):
        repo = HistoryRepository(conn)
        repo.add_entry(user_id, "dinner", 5, 1000, "optimal", "2026-04-19")
        repo.clear(user_id)
        _, total = repo.list_entries(user_id)
        assert total == 0

    def test_trim(self, conn, user_id):
        repo = HistoryRepository(conn)
        for i in range(15):
            repo.add_entry(user_id, "dinner", 5, 1000, "optimal", f"2026-04-{i + 1}")
        repo.trim(user_id, max_entries=10)
        _, total = repo.list_entries(user_id)
        assert total == 10

    def test_get_entry(self, conn, user_id):
        repo = HistoryRepository(conn)
        entry_id = repo.add_entry(user_id, "dinner", 5, 1000, "optimal", "2026-04-19")
        entry = repo.get_entry(user_id, entry_id)
        assert entry is not None
        assert entry["profile_name"] == "dinner"

    def test_user_isolation(self, conn):
        conn.execute("INSERT INTO users (username, password_hash) VALUES ('a', '')")
        conn.execute("INSERT INTO users (username, password_hash) VALUES ('b', '')")
        conn.commit()
        uid_a = conn.execute("SELECT id FROM users WHERE username='a'").fetchone()[0]
        uid_b = conn.execute("SELECT id FROM users WHERE username='b'").fetchone()[0]

        repo = HistoryRepository(conn)
        repo.add_entry(uid_a, "dinner", 5, 1000, "optimal", "2026-04-19")
        repo.add_entry(uid_b, "lunch", 3, 500, "optimal", "2026-04-19")

        entries_a, _ = repo.list_entries(uid_a)
        entries_b, _ = repo.list_entries(uid_b)
        assert len(entries_a) == 1
        assert entries_a[0]["profile_name"] == "dinner"
        assert len(entries_b) == 1
        assert entries_b[0]["profile_name"] == "lunch"
