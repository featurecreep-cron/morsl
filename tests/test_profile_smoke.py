"""Smoke test: run each JSON profile through the solver.
Validates that all profiles can successfully select recipes."""

from __future__ import annotations

import os

import pytest


def get_env_credentials():
    """Load Tandoor credentials from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        pytest.skip("No .env file found - skipping live API tests")

    env = {}
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                env[key] = val

    if "TANDOOR_URL" not in env or "TANDOOR_TOKEN" not in env:
        pytest.skip("TANDOOR_URL and TANDOOR_TOKEN not in .env")

    return env["TANDOOR_URL"], env["TANDOOR_TOKEN"]


@pytest.fixture(scope="module")
def credentials():
    """Fixture providing Tandoor API credentials."""
    return get_env_credentials()


@pytest.fixture(scope="module")
def config_service():
    """Fixture providing ConfigService instance."""
    from morsl.services.config_service import ConfigService

    return ConfigService()


def get_profile_names():
    """Get list of all profile names for parametrization."""
    from morsl.services.config_service import ConfigService

    cs = ConfigService()
    return [p.name for p in cs.list_profiles()]


@pytest.mark.integration
@pytest.mark.parametrize("profile_name", get_profile_names())
def test_profile_generates_recipes(profile_name, credentials, config_service):
    """Test that each profile can successfully generate recipes."""
    import logging

    from services.menu_service import MenuService

    url, token = credentials

    # Set up minimal logging
    logger = logging.getLogger(f"test_{profile_name}")
    logger.setLevel(logging.WARNING)
    logger.loglevel = 30  # Required by tandoor_api

    # Load profile
    config = config_service.load_profile(profile_name)
    constraints = config.get("constraints", [])

    # Skip profiles with no constraints (they just pick random recipes)
    if not constraints:
        pytest.skip(f"Profile {profile_name} has no constraints")

    # Run the solver
    ms = MenuService(url, token, config, logger)
    ms.prepare_data()

    # Should not raise
    result = ms.select_recipes()

    # Verify results
    assert result.status == "optimal", f"Solver failed for {profile_name}: {result.status}"
    assert len(result.recipes) > 0, f"No recipes selected for {profile_name}"
    assert len(result.recipes) <= config.get("choices", 7), f"Too many recipes for {profile_name}"


@pytest.mark.parametrize("profile_name", get_profile_names())
def test_profile_constraint_structure(profile_name, config_service):
    """Test that each profile has valid constraint structure."""
    config = config_service.load_profile(profile_name)
    constraints = config.get("constraints", [])

    for i, c in enumerate(constraints):
        # Required fields
        assert "type" in c, f"constraints[{i}] missing 'type'"
        assert "operator" in c, f"constraints[{i}] missing 'operator'"

        ctype = c["type"]
        assert ctype in (
            "keyword",
            "food",
            "book",
            "rating",
            "cookedon",
            "createdon",
        ), f"Invalid constraint type: {ctype}"

        # Type-specific validation
        if ctype in ("keyword", "food", "book"):
            assert "items" in c, f"constraints[{i}] ({ctype}) missing 'items'"
            assert isinstance(c["items"], list), f"constraints[{i}] 'items' not a list"
            for j, item in enumerate(c["items"]):
                assert "id" in item, f"constraints[{i}].items[{j}] missing 'id'"

        # Operator validation
        assert c["operator"] in (
            ">=",
            "<=",
            "==",
            "!=",
            "between",
        ), f"Invalid operator: {c['operator']}"
