"""One-time migration: import existing JSON files into SQLite.

Reads data/ JSON files and inserts them as user_id=1 (the original
single-tenant user). Non-destructive — JSON files are not deleted.
Idempotent — skips if user already exists in database.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from morsl.db import get_db, json_col

logger = logging.getLogger(__name__)


def migrate(data_dir: str = "data") -> bool:
    """Run the JSON-to-SQLite migration. Returns True if migration was performed."""
    conn = get_db(data_dir)

    # Check if migration already ran
    row = conn.execute("SELECT id FROM users WHERE id = 1").fetchone()
    if row is not None:
        logger.debug("Migration already complete — user 1 exists")
        return False

    logger.info("Starting JSON → SQLite migration")

    # Create the default user
    conn.execute("INSERT INTO users (id, username, password_hash) VALUES (1, 'admin', '')")

    _migrate_settings(conn, data_dir)
    _migrate_profiles(conn, data_dir)
    _migrate_menu(conn, data_dir)
    _migrate_templates(conn, data_dir)
    _migrate_history(conn, data_dir)

    conn.commit()
    logger.info("JSON → SQLite migration complete")
    return True


def _migrate_settings(conn, data_dir: str) -> None:
    """Import settings.json into the settings table."""
    path = os.path.join(data_dir, "settings.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Skipping settings migration: %s", e)
        return

    for key, value in settings.items():
        conn.execute(
            "INSERT INTO settings (user_id, key, value) VALUES (1, ?, ?)",
            (key, json_col(value)),
        )
    logger.info("Migrated %d settings", len(settings))


def _migrate_profiles(conn, data_dir: str) -> None:
    """Import data/profiles/*.json into the profiles table."""
    profiles_dir = os.path.join(data_dir, "profiles")
    if not os.path.isdir(profiles_dir):
        return

    count = 0
    for filename in sorted(os.listdir(profiles_dir)):
        if not filename.endswith(".json"):
            continue
        name = Path(filename).stem
        if name == "base":
            # Store base config as a special profile
            pass
        path = os.path.join(profiles_dir, filename)
        try:
            with open(path) as f:
                config = json.load(f)
            is_default = 1 if config.get("default", False) else 0
            conn.execute(
                "INSERT INTO profiles (user_id, name, config, is_default) VALUES (1, ?, ?, ?)",
                (name, json_col(config), is_default),
            )
            count += 1
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipping profile '%s': %s", name, e)

    logger.info("Migrated %d profiles", count)


def _migrate_menu(conn, data_dir: str) -> None:
    """Import current_menu.json into the menus table."""
    path = os.path.join(data_dir, "current_menu.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path) as f:
            menu = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Skipping menu migration: %s", e)
        return

    recipes = menu.get("recipes", [])
    generated_at = menu.get("generated_at", "")
    profile = menu.get("profile", "default")
    metadata = {k: v for k, v in menu.items() if k not in ("recipes", "generated_at", "profile")}

    conn.execute(
        "INSERT INTO menus (user_id, profile_name, recipes, generated_at, "
        "metadata, is_current) VALUES (1, ?, ?, ?, ?, 1)",
        (profile, json_col(recipes), generated_at, json_col(metadata) if metadata else None),
    )
    logger.info("Migrated current menu (%d recipes)", len(recipes))


def _migrate_templates(conn, data_dir: str) -> None:
    """Import data/templates/*.json into the templates table."""
    templates_dir = os.path.join(data_dir, "templates")
    if not os.path.isdir(templates_dir):
        return

    count = 0
    for filename in sorted(os.listdir(templates_dir)):
        if not filename.endswith(".json"):
            continue
        name = Path(filename).stem
        path = os.path.join(templates_dir, filename)
        try:
            with open(path) as f:
                config = json.load(f)
            conn.execute(
                "INSERT INTO templates (user_id, name, config) VALUES (1, ?, ?)",
                (name, json_col(config)),
            )
            count += 1
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipping template '%s': %s", name, e)

    logger.info("Migrated %d templates", count)


def _migrate_history(conn, data_dir: str) -> None:
    """Import generation_history.json into the generation_history table."""
    path = os.path.join(data_dir, "generation_history.json")
    if not os.path.isfile(path):
        return
    try:
        with open(path) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Skipping history migration: %s", e)
        return

    if not isinstance(entries, list):
        logger.warning("generation_history.json is not a list — skipping")
        return

    count = 0
    for entry in entries:
        profile = entry.get("profile", "unknown")
        recipe_count = entry.get("recipe_count", 0)
        duration_ms = entry.get("duration_ms", 0)
        status = entry.get("status", "unknown")
        generated_at = entry.get("generated_at", "")
        metadata = {
            k: v
            for k, v in entry.items()
            if k not in ("profile", "recipe_count", "duration_ms", "status", "generated_at", "id")
        }
        conn.execute(
            "INSERT INTO generation_history "
            "(user_id, profile_name, recipe_count, duration_ms, status, "
            "generated_at, metadata) VALUES (1, ?, ?, ?, ?, ?, ?)",
            (
                profile,
                recipe_count,
                duration_ms,
                status,
                generated_at,
                json_col(metadata) if metadata else None,
            ),
        )
        count += 1

    logger.info("Migrated %d history entries", count)
