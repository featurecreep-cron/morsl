from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from morsl.constants import API_CACHE_TTL_MINUTES
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationService, GenerationState
from morsl.services.menu_service import (
    MenuService,
    _apply_date_filters,
    _build_rating_condition,
    _resolve_date_recipes,
)


def _make_mock_provider():
    """Create a MagicMock suitable for use as a RecipeProvider."""
    return MagicMock()


class TestMenuService:
    def test_init_with_defaults(self, mock_logger):
        config = {
            "choices": 5,
            "cache": API_CACHE_TTL_MINUTES,
            "constraints": [],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.choices == 5
        assert service.min_choices is None

    def test_init_with_min_choices(self, mock_logger):
        config = {
            "choices": 5,
            "min_choices": 3,
            "cache": 0,
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.min_choices == 3

    def test_parse_constraints_v2_format(self, mock_logger):
        """Test parsing v2 constraint format."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 1, "name": "Test"}],
                    "count": 3,
                    "operator": ">=",
                },
                {
                    "type": "food",
                    "items": [{"id": 10, "name": "Whiskey"}],
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())

        assert len(service.constraints) == 2
        assert service.constraints[0]["type"] == "keyword"
        assert service.constraints[0]["item_ids"] == [1]
        assert service.constraints[0]["count"] == 3
        assert service.constraints[1]["type"] == "food"
        assert service.constraints[1]["item_ids"] == [10]

    def test_parse_constraints_with_except(self, mock_logger):
        """Test parsing constraints with except clause."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "food",
                    "items": [{"id": 1, "name": "Syrup"}],
                    "except": [{"id": 2, "name": "Sugar Syrup"}],
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())

        assert service.constraints[0]["except_ids"] == [2]

    def test_parse_constraints_empty(self, mock_logger):
        config = {"choices": 5, "cache": 0, "constraints": []}
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.constraints == []

    def test_prepare_recipes_all(self, mock_logger):
        config = {"choices": 2, "cache": 0, "constraints": []}
        mock_recipe_data = [
            {
                "id": 1,
                "name": "R1",
                "description": "",
                "new": False,
                "servings": 4,
                "keywords": [],
                "rating": 3.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            },
        ]
        provider = _make_mock_provider()
        provider.get_recipes.return_value = mock_recipe_data
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_recipes()
        assert len(service.recipes) == 1
        assert service.recipes[0].id == 1

    def test_parse_makenow_constraint(self, mock_logger):
        """Test parsing a makenow constraint."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {"type": "makenow", "count": 3, "operator": ">="},
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert len(service.constraints) == 1
        assert service.constraints[0]["type"] == "makenow"
        assert service.constraints[0]["count"] == 3

    def test_prepare_makenow_constraint(self, mock_logger):
        """Test that makenow constraint fetches on-hand recipes from provider."""
        pool_recipes = [
            {
                "id": 1,
                "name": "R1",
                "description": "",
                "new": False,
                "servings": 4,
                "keywords": [],
                "rating": 3.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            },
            {
                "id": 2,
                "name": "R2",
                "description": "",
                "new": False,
                "servings": 4,
                "keywords": [],
                "rating": 4.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            },
        ]
        # Only recipe 1 is makeable with on-hand ingredients
        onhand_recipes = [pool_recipes[0]]

        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {"type": "makenow", "count": 1, "operator": ">="},
            ],
        }
        provider = _make_mock_provider()
        provider.get_recipes.side_effect = lambda **kwargs: (
            onhand_recipes if kwargs.get("params", {}).get("makenow") else pool_recipes
        )
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_recipes()
        service.prepare_constraints()

        assert len(service.constraints[0]["matching_recipes"]) == 1
        assert service.constraints[0]["matching_recipes"][0].id == 1

    def test_prepare_recipes_with_filters(self, mock_logger):
        """Test that filters config passes CustomFilter IDs to provider."""
        config = {"choices": 2, "cache": 0, "filters": [42, 99], "constraints": []}
        mock_recipe_data = [
            {
                "id": 1,
                "name": "R1",
                "description": "",
                "new": False,
                "servings": 4,
                "keywords": [],
                "rating": 3.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            },
        ]
        provider = _make_mock_provider()
        provider.get_recipes.return_value = mock_recipe_data
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_recipes()
        provider.get_recipes.assert_called_once_with(params=None, filters=[42, 99])
        assert len(service.recipes) == 1

    def test_parse_date_constraint_cooked(self, mock_logger):
        """Test parsing cooked date constraint with older_than_days."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "cookedon",
                    "count": 2,
                    "operator": ">=",
                    "cooked": {"older_than_days": 7},
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.constraints[0]["cooked_date"] is not None
        assert service.constraints[0]["cooked_after"] is False

    def test_parse_date_constraint_cooked_within(self, mock_logger):
        """Test parsing cooked date constraint with within_days (mirror branch)."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "cookedon",
                    "count": 1,
                    "operator": ">=",
                    "cooked": {"within_days": 14},
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.constraints[0]["cooked_date"] is not None
        assert service.constraints[0]["cooked_after"] is True

    def test_parse_date_constraint_created_older(self, mock_logger):
        """Test parsing created date constraint with older_than_days (mirror branch)."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "createdon",
                    "count": 1,
                    "operator": ">=",
                    "created": {"older_than_days": 90},
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.constraints[0]["created_date"] is not None
        assert service.constraints[0]["created_after"] is False

    def test_parse_date_constraint_created_within(self, mock_logger):
        """Test parsing created date constraint with within_days."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "createdon",
                    "count": 1,
                    "operator": ">=",
                    "created": {"within_days": 30},
                },
            ],
        }
        service = MenuService(config=config, logger=mock_logger, provider=_make_mock_provider())
        assert service.constraints[0]["created_date"] is not None
        assert service.constraints[0]["created_after"] is True


class TestBuildRatingCondition:
    def test_unrated(self):
        assert _build_rating_condition({"unrated": True}) == 0

    def test_min_and_max(self):
        assert _build_rating_condition({"min": 3, "max": 5}) == [3, 5]

    def test_min_only(self):
        assert _build_rating_condition({"min": 4}) == 4

    def test_max_only(self):
        assert _build_rating_condition({"max": 3}) == -3

    def test_no_rating(self):
        assert _build_rating_condition({}) is None


class TestPantryConstraint:
    """Tests for the pantry flag auto-injecting a soft makenow constraint."""

    def test_pantry_flag_injects_makenow(self, mock_logger):
        provider = _make_mock_provider()
        from morsl.providers.base import Capability

        provider.capabilities.return_value = Capability.ONHAND
        provider.get_recipes.return_value = []

        config = {"choices": 3, "pantry": True, "constraints": []}
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_constraints()

        makenow = [c for c in service.constraints if c.get("type") == "makenow"]
        assert len(makenow) == 1
        assert makenow[0]["soft"] is True
        assert makenow[0]["weight"] == 5  # DEFAULT_PANTRY_WEIGHT

    def test_pantry_flag_skips_when_makenow_exists(self, mock_logger):
        provider = _make_mock_provider()
        from morsl.providers.base import Capability

        provider.capabilities.return_value = Capability.ONHAND
        provider.get_recipes.return_value = []

        config = {
            "choices": 3,
            "pantry": True,
            "constraints": [{"type": "makenow", "count": 2, "operator": ">="}],
        }
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_constraints()

        makenow = [c for c in service.constraints if c.get("type") == "makenow"]
        assert len(makenow) == 1  # only the original, no duplicate

    def test_pantry_flag_skips_without_capability(self, mock_logger):
        provider = _make_mock_provider()
        from morsl.providers.base import Capability

        provider.capabilities.return_value = Capability.MEAL_PLAN  # no ONHAND

        config = {"choices": 3, "pantry": True, "constraints": []}
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_constraints()

        makenow = [c for c in service.constraints if c.get("type") == "makenow"]
        assert len(makenow) == 0

    def test_no_pantry_flag_no_injection(self, mock_logger):
        provider = _make_mock_provider()
        config = {"choices": 3, "constraints": []}
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_constraints()

        makenow = [c for c in service.constraints if c.get("type") == "makenow"]
        assert len(makenow) == 0

    def test_custom_pantry_weight(self, mock_logger):
        provider = _make_mock_provider()
        from morsl.providers.base import Capability

        provider.capabilities.return_value = Capability.ONHAND
        provider.get_recipes.return_value = []

        config = {"choices": 3, "pantry": True, "pantry_weight": 20, "constraints": []}
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_constraints()

        makenow = [c for c in service.constraints if c.get("type") == "makenow"]
        assert makenow[0]["weight"] == 20


# Tandoor-shaped API response fixtures for integration tests
_RECIPE_POOL = [
    {
        "id": i,
        "name": name,
        "description": "",
        "new": False,
        "servings": 4,
        "keywords": kws,
        "rating": rating,
        "last_cooked": cooked,
        "created_at": "2024-01-01T12:00:00+00:00",
    }
    for i, name, kws, rating, cooked in [
        (
            1,
            "Margarita",
            [{"id": 10, "name": "Tequila"}, {"id": 20, "name": "Citrus"}],
            4.5,
            "2024-12-01T12:00:00+00:00",
        ),
        (2, "Old Fashioned", [{"id": 30, "name": "Whiskey"}], 5.0, None),
        (
            3,
            "Daiquiri",
            [{"id": 10, "name": "Tequila"}, {"id": 40, "name": "Rum"}],
            3.0,
            "2024-06-01T12:00:00+00:00",
        ),
        (4, "Mojito", [{"id": 40, "name": "Rum"}, {"id": 20, "name": "Citrus"}], 2.0, None),
        (5, "Negroni", [{"id": 50, "name": "Gin"}], 4.0, "2024-11-01T12:00:00+00:00"),
    ]
]


class TestMenuServiceIntegration:
    """Tests that exercise prepare_data + select_recipes end-to-end with mocked provider."""

    def _make_service(self, mock_logger, config, provider_setup):
        """Build a MenuService with mocked provider."""
        provider = _make_mock_provider()
        provider_setup(provider)
        service = MenuService(config=config, logger=mock_logger, provider=provider)
        service.prepare_data()
        return service

    def test_keyword_constraint_end_to_end(self, mock_logger):
        """Full pipeline: load recipes, prepare keyword constraint, solve."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 10, "name": "Tequila"}],
                    "count": 1,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL
            provider.get_tag_tree.return_value = [{"id": 10, "name": "Tequila"}]

        service = self._make_service(mock_logger, config, setup)

        # Verify keyword constraint was prepared
        assert len(service.constraints[0]["keywords"]) == 1
        assert service.constraints[0]["keywords"][0].id == 10

        # Run solver — should succeed with keyword constraint
        result = service.select_recipes()
        assert len(result.recipes) == 2
        assert result.constraint_count == 1
        # At least one recipe must have keyword 10
        has_tequila = any(10 in r.keywords for r in result.recipes)
        assert has_tequila

    def test_keyword_constraint_no_children(self, mock_logger):
        """Keyword constraint with include_children=False uses get_tag instead of tree."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 50, "name": "Gin"}],
                    "count": 1,
                    "operator": ">=",
                    "include_children": False,
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL
            provider.get_tag.return_value = {"id": 50, "name": "Gin"}

        service = self._make_service(mock_logger, config, setup)
        service.provider.get_tag.assert_called_once_with(50)

    def test_food_constraint_end_to_end(self, mock_logger):
        """Full pipeline with food constraint — fetches ingredient, queries matching recipes."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "food",
                    "items": [{"id": 100, "name": "Lime Juice"}],
                    "count": 1,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.side_effect = lambda **kwargs: (
                _RECIPE_POOL[:3]  # recipes containing lime juice
                if kwargs.get("params", {}).get("foods_or")
                else _RECIPE_POOL
            )
            provider.get_ingredient.return_value = {"id": 100, "name": "Lime Juice"}

        service = self._make_service(mock_logger, config, setup)
        assert len(service.constraints[0]["foods"]) == 1
        assert len(service.constraints[0]["matching_recipes"]) == 3
        result = service.select_recipes()
        assert result.constraint_count == 1

    def test_food_constraint_with_except(self, mock_logger):
        """Food constraint with except_ids passes foods_or_not to provider."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "food",
                    "items": [{"id": 100, "name": "Citrus"}],
                    "except": [{"id": 101, "name": "Lemon"}],
                    "count": 1,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.side_effect = lambda **kwargs: (
                _RECIPE_POOL[:2] if kwargs.get("params", {}).get("foods_or") else _RECIPE_POOL
            )
            provider.get_ingredient.return_value = {"id": 100, "name": "Citrus"}

        service = self._make_service(mock_logger, config, setup)
        # Check that except_ids were parsed
        assert service.constraints[0]["except_ids"] == [101]

    def test_book_constraint_end_to_end(self, mock_logger):
        """Full pipeline with collection constraint."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "book",
                    "items": [{"id": 5, "name": "Classics"}],
                    "count": 1,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL
            provider.get_collection.return_value = {"id": 5, "name": "Classics", "filter": None}
            provider.get_collection_recipes.return_value = [_RECIPE_POOL[0], _RECIPE_POOL[1]]

        service = self._make_service(mock_logger, config, setup)
        assert len(service.constraints[0]["books"]) == 1
        assert len(service.constraints[0]["matching_recipes"]) == 2
        result = service.select_recipes()
        assert result.constraint_count == 1

    def test_rating_constraint_end_to_end(self, mock_logger):
        """Full pipeline with rating constraint — min 4 stars."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "rating",
                    "min": 4,
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        # All selected recipes should be 4+ stars
        for r in result.recipes:
            assert r.rating >= 4.0

    def test_multiple_constraints(self, mock_logger):
        """Multiple constraint types in one solve."""
        config = {
            "choices": 3,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 20, "name": "Citrus"}],
                    "count": 1,
                    "operator": ">=",
                },
                {
                    "type": "rating",
                    "min": 3,
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL
            provider.get_tag_tree.return_value = [{"id": 20, "name": "Citrus"}]

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        assert result.constraint_count == 2
        assert len(result.recipes) == 3

    def test_exclude_constraint(self, mock_logger):
        """Exclude constraint inverts match set — requires picks from non-matching recipes."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 40, "name": "Rum"}],
                    "count": 2,
                    "operator": ">=",
                    "exclude": True,
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL
            provider.get_tag_tree.return_value = [{"id": 40, "name": "Rum"}]

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        # With exclude=True, the constraint says "at least 2 non-rum recipes"
        # Since we pick 2 total and require 2 non-rum, none should have rum
        non_rum = [r for r in result.recipes if 40 not in r.keywords]
        assert len(non_rum) >= 2

    def test_soft_constraint(self, mock_logger):
        """Soft constraint can be relaxed when infeasible."""
        config = {
            "choices": 3,
            "cache": 0,
            "constraints": [
                {
                    "type": "rating",
                    "min": 5,
                    "count": 3,
                    "operator": ">=",
                    "soft": True,
                    "label": "All 5 stars",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        # Only 1 recipe has 5 stars, but constraint is soft so solver relaxes
        assert len(result.recipes) == 3
        assert result.status in ("optimal", "relaxed")

    def test_select_with_cookedon_constraint(self, mock_logger):
        """Cookedon date constraint filters by last_cooked."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "cookedon",
                    "count": 1,
                    "operator": ">=",
                    "older_than_days": 180,
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        assert result.constraint_count == 1

    def test_makenow_constraint_in_solver(self, mock_logger):
        """Makenow constraint flows through solver — applies via book constraint method."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {"type": "makenow", "count": 1, "operator": ">="},
            ],
        }
        onhand = _RECIPE_POOL[:2]

        def setup(provider):
            provider.get_recipes.side_effect = lambda **kwargs: (
                onhand if kwargs.get("params", {}).get("makenow") else _RECIPE_POOL
            )

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        assert result.constraint_count == 1
        # At least one recipe should be from the on-hand set
        onhand_ids = {r["id"] for r in onhand}
        assert any(r.id in onhand_ids for r in result.recipes)

    def test_food_constraint_tolerates_api_error(self, mock_logger):
        """Food constraint skips ingredients that fail to fetch but still finds recipes."""
        from morsl.tandoor_api import TandoorAPIError

        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "food",
                    "items": [{"id": 100, "name": "Lime"}, {"id": 101, "name": "Missing"}],
                    "count": 1,
                    "operator": ">=",
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.side_effect = lambda **kwargs: (
                _RECIPE_POOL[:2] if kwargs.get("params", {}).get("foods_or") else _RECIPE_POOL
            )

            def get_ingredient_side_effect(food_id, **kwargs):
                if food_id == 101:
                    raise TandoorAPIError(404, "Not found")
                return {"id": 100, "name": "Lime"}

            provider.get_ingredient.side_effect = get_ingredient_side_effect

        service = self._make_service(mock_logger, config, setup)
        # Should have 1 food (the other was skipped due to error)
        assert len(service.constraints[0]["foods"]) == 1
        assert service.constraints[0]["foods"][0].name == "Lime"

    def test_select_with_cookedon_within_days(self, mock_logger):
        """Cookedon constraint with within_days (the other date branch)."""
        config = {
            "choices": 2,
            "cache": 0,
            "constraints": [
                {
                    "type": "cookedon",
                    "count": 1,
                    "operator": ">=",
                    "within_days": 900,
                },
            ],
        }

        def setup(provider):
            provider.get_recipes.return_value = _RECIPE_POOL

        service = self._make_service(mock_logger, config, setup)
        result = service.select_recipes()
        assert result.constraint_count == 1


class TestDateFilterFunctions:
    """Test the date helper functions that are called during constraint application."""

    def test_resolve_date_recipes_no_filter(self):
        """No within_days or older_than_days returns all recipes."""
        from morsl.models import make_recipe

        recipes = [make_recipe(r) for r in _RECIPE_POOL]
        result = _resolve_date_recipes(recipes, {}, "cookedon")
        assert len(result) == len(recipes)

    def test_apply_date_filters_no_dates(self):
        """No cooked_date or created_date in constraint returns recipes unchanged."""
        from morsl.models import make_recipe

        recipes = [make_recipe(r) for r in _RECIPE_POOL]
        result = _apply_date_filters(recipes, {})
        assert result == recipes

    def test_apply_date_filters_with_cooked(self):
        """Apply cooked_date filter narrows results."""
        from morsl.models import make_recipe
        from morsl.utils import now

        recipes = [make_recipe(r) for r in _RECIPE_POOL]
        cutoff = now()
        result = _apply_date_filters(recipes, {"cooked_date": cutoff, "cooked_after": False})
        for r in result:
            assert r.cookedon is not None
            assert r.cookedon < cutoff

    def test_apply_date_filters_with_created(self):
        """Apply created_date filter (the other branch)."""
        from morsl.models import make_recipe
        from morsl.utils import now

        recipes = [make_recipe(r) for r in _RECIPE_POOL]
        cutoff = now()
        result = _apply_date_filters(recipes, {"created_date": cutoff, "created_after": False})
        for r in result:
            assert r.createdon is not None
            assert r.createdon < cutoff

    def test_resolve_date_recipes_within_days(self):
        """within_days branch of _resolve_date_recipes."""
        from morsl.models import make_recipe

        recipes = [make_recipe(r) for r in _RECIPE_POOL]
        result = _resolve_date_recipes(recipes, {"within_days": 365}, "cookedon")
        # Should return recipes cooked within last 365 days
        for r in result:
            assert r.cookedon is not None


class TestConfigService:
    def test_load_profile(self, tmp_path):
        """Test loading a v2 JSON profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(
            json.dumps({"cache": 120, "choices": 3, "constraints": []})
        )
        (profiles_dir / "test.json").write_text(
            json.dumps(
                {
                    "choices": 7,
                    "constraints": [
                        {
                            "type": "keyword",
                            "items": [{"id": 1, "name": "Test"}],
                            "count": 7,
                            "operator": "==",
                        }
                    ],
                }
            )
        )

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("test")
        assert config["choices"] == 7
        assert config["cache"] == 120  # inherited from base
        assert len(config["constraints"]) == 1

    def test_load_profile_no_base(self, tmp_path):
        """Test loading profile without a base."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "solo.json").write_text(json.dumps({"choices": 4}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("solo")
        assert config["choices"] == 4

    def test_load_profile_missing(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Profile not found"):
            svc.load_profile("nonexistent")

    def test_list_profiles(self, tmp_path):
        """Test listing profiles shows constraint count."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(json.dumps({"choices": 5}))
        (profiles_dir / "weekday.json").write_text(
            json.dumps(
                {
                    "choices": 5,
                    "constraints": [
                        {"type": "keyword", "items": [], "count": 1, "operator": ">="}
                    ],
                }
            )
        )
        (profiles_dir / "weekend.json").write_text(json.dumps({"choices": 3, "constraints": []}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        profiles = svc.list_profiles()
        assert len(profiles) == 2
        names = [p.name for p in profiles]
        assert "weekday" in names
        assert "weekend" in names
        # base.json should not appear
        assert "base" not in names

        # Check constraint count
        weekday = next(p for p in profiles if p.name == "weekday")
        assert weekday.constraint_count == 1

    def test_list_profiles_empty_dir(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        assert svc.list_profiles() == []

    def test_list_profiles_nonexistent_dir(self):
        svc = ConfigService(profiles_dir="/nonexistent")
        assert svc.list_profiles() == []

    def test_profile_constraints_concatenated(self, tmp_path):
        """Test that constraints from base and profile are concatenated."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(
            json.dumps(
                {
                    "cache": API_CACHE_TTL_MINUTES,
                    "choices": 5,
                    "constraints": [
                        {
                            "type": "keyword",
                            "items": [{"id": 1, "name": "Base KW"}],
                            "count": 1,
                            "operator": ">=",
                        }
                    ],
                }
            )
        )
        (profiles_dir / "custom.json").write_text(
            json.dumps(
                {
                    "choices": 3,
                    "constraints": [
                        {
                            "type": "food",
                            "items": [{"id": 10, "name": "Whiskey"}],
                            "count": 2,
                            "operator": ">=",
                        }
                    ],
                }
            )
        )

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("custom")
        # choices overridden, constraints concatenated
        assert config["choices"] == 3
        assert len(config["constraints"]) == 2
        assert config["constraints"][0]["type"] == "keyword"
        assert config["constraints"][1]["type"] == "food"

    def test_create_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        svc = ConfigService(profiles_dir=str(profiles_dir))

        result = svc.create_profile("new_profile", {"choices": 7, "description": "Fresh"})
        assert result["choices"] == 7
        assert (profiles_dir / "new_profile.json").is_file()

    def test_create_profile_duplicate_raises(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "existing.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        with pytest.raises(FileExistsError):
            svc.create_profile("existing", {"choices": 5})

    def test_update_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "editable.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        result = svc.update_profile("editable", {"choices": 12})
        assert result["choices"] == 12

        saved = json.loads((profiles_dir / "editable.json").read_text())
        assert saved["choices"] == 12

    def test_update_profile_not_found(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            svc.update_profile("ghost", {"choices": 5})

    def test_delete_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "doomed.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        svc.delete_profile("doomed")
        assert not (profiles_dir / "doomed.json").is_file()

    def test_delete_profile_not_found(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            svc.delete_profile("ghost")

    def test_get_profile_raw(self, tmp_path):
        """Test getting raw profile without base merge."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(json.dumps({"cache": 300, "choices": 5}))
        (profiles_dir / "child.json").write_text(json.dumps({"choices": 8}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        raw = svc.get_profile_raw("child")
        assert raw["choices"] == 8
        assert "cache" not in raw  # Not merged with base

    @pytest.mark.parametrize(
        "name",
        [
            "../../settings",
            "../secret",
            "foo/bar",
            "",
            ".hidden",
        ],
    )
    def test_path_traversal_blocked(self, tmp_path, name):
        """Profile names with path separators or leading dots are rejected."""
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.get_profile_raw(name)
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.load_profile(name)
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.update_profile(name, {"choices": 5})
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.delete_profile(name)


@pytest.mark.slow
class TestOnHandSubstitution:
    """Tests for on-hand food substitution in GenerationService._sync_generate()."""

    def _make_solver_result(self):
        from morsl.models import SolverResult, make_recipe

        r = make_recipe(
            {
                "id": 1,
                "name": "Mojito",
                "description": "Minty",
                "new": False,
                "servings": 1,
                "keywords": [],
                "rating": 4.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            }
        )
        return SolverResult(recipes=(r,), requested_count=1, constraint_count=0)

    def _make_details(self, food_onhand=False):
        return {
            "image": "http://img/mojito.jpg",
            "working_time": 5,
            "cooking_time": 0,
            "steps": [
                {
                    "name": "Mix",
                    "instruction": "Muddle mint and lime.",
                    "time": 5,
                    "order": 0,
                    "ingredients": [
                        {
                            "amount": 2,
                            "unit": {"name": "oz"},
                            "food": {"id": 100, "name": "Lime Juice", "food_onhand": food_onhand},
                        }
                    ],
                }
            ],
        }

    def test_substitution_when_not_onhand(self, mock_logger):
        """When food is not on hand, substitute with an on-hand alternative."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.provider = MagicMock()
            ms.provider.get_recipe_details.return_value = self._make_details(food_onhand=False)
            ms.provider.get_ingredient_substitutes.return_value = [{"id": 200}]
            ms.provider.get_ingredient.return_value = {
                "id": 200,
                "name": "Lemon Juice",
                "food_onhand": True,
            }

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert len(result["recipes"]) == 1
        assert result["recipes"][0]["ingredients"][0]["food"] == "Lemon Juice"
        ms.provider.get_ingredient_substitutes.assert_called_once_with(100, substitute_type="food")

    def test_no_substitution_when_onhand(self, mock_logger):
        """When food is already on hand, no substitution occurs."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.provider = MagicMock()
            ms.provider.get_recipe_details.return_value = self._make_details(food_onhand=True)

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert result["recipes"][0]["ingredients"][0]["food"] == "Lime Juice"
        ms.provider.get_ingredient_substitutes.assert_not_called()

    def test_steps_and_timing_extracted(self, mock_logger):
        """Steps and timing are extracted from recipe details."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.provider = MagicMock()
            ms.provider.get_recipe_details.return_value = self._make_details(food_onhand=True)

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        recipe = result["recipes"][0]
        assert recipe["working_time"] == 5
        assert recipe["cooking_time"] == 0
        assert len(recipe["steps"]) == 1
        assert recipe["steps"][0]["name"] == "Mix"
        assert recipe["steps"][0]["instruction"] == "Muddle mint and lime."
        assert recipe["steps"][0]["time"] == 5
        assert recipe["steps"][0]["order"] == 0

    def test_substitution_no_subs_available(self, mock_logger):
        """When no substitutes are available, keep original food."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.provider = MagicMock()
            ms.provider.get_recipe_details.return_value = self._make_details(food_onhand=False)
            ms.provider.get_ingredient_substitutes.return_value = []

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert result["recipes"][0]["ingredients"][0]["food"] == "Lime Juice"


class TestGenerationService:
    def test_initial_state_idle(self):
        svc = GenerationService(data_dir="/tmp/test_gen")
        status = svc.get_status()
        assert status.state == GenerationState.IDLE
        assert status.request_id is None

    def test_get_current_menu_none(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        assert svc.get_current_menu() is None

    def test_get_current_menu_from_file(self, tmp_path):
        menu_data = {"recipes": [{"id": 1, "name": "Test"}], "generated_at": "2024-01-01T00:00:00"}
        (tmp_path / "current_menu.json").write_text(json.dumps(menu_data))

        svc = GenerationService(data_dir=str(tmp_path))
        result = svc.get_current_menu()
        assert result is not None
        assert len(result["recipes"]) == 1

    def test_save_menu_atomic(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        menu_data = {"recipes": [], "generated_at": "2024-01-01T00:00:00"}
        svc._save_menu(menu_data)

        saved = json.loads((tmp_path / "current_menu.json").read_text())
        assert saved["generated_at"] == "2024-01-01T00:00:00"

    def test_start_generation_returns_request_id(self, mock_logger, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        config = {"choices": 5, "cache": 0}

        loop = asyncio.new_event_loop()
        try:
            # We mock _sync_generate to avoid actual solver execution
            with patch.object(
                svc,
                "_sync_generate",
                return_value={
                    "recipes": [{"id": 1, "name": "Test", "description": "", "rating": 3.0}],
                    "generated_at": "2024-01-01T00:00:00",
                    "requested_count": 5,
                    "constraint_count": 0,
                    "status": "optimal",
                    "warnings": [],
                    "relaxed_constraints": [],
                },
            ):
                request_id = loop.run_until_complete(self._async_start(svc, config, mock_logger))
            assert request_id is not None
            assert len(request_id) == 36  # UUID format
        finally:
            loop.close()

    async def _async_start(self, svc, config, logger):
        request_id = await svc.start_generation(
            config=config, url="http://localhost", token="test", logger=logger
        )
        # Wait for task to complete
        if svc._current_task:
            await svc._current_task
        return request_id

    def test_duplicate_generation_raises(self, mock_logger, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        svc._status.state = GenerationState.GENERATING
        with pytest.raises(RuntimeError, match="already in progress"):  # noqa: PT012
            # Must run in event loop context
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._async_start(svc, {}, mock_logger))
            finally:
                loop.close()

    def test_clear_menu(self, tmp_path):
        menu_data = {"recipes": [{"id": 1, "name": "Test"}]}
        (tmp_path / "current_menu.json").write_text(json.dumps(menu_data))
        svc = GenerationService(data_dir=str(tmp_path))
        assert svc.get_current_menu() is not None

        result = svc.clear_menu()
        assert result is True
        assert svc.get_current_menu() is None
        assert not (tmp_path / "current_menu.json").exists()

    def test_clear_menu_nothing_to_clear(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        result = svc.clear_menu()
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_completion_no_task(self, tmp_path):
        """wait_for_completion returns current status when no task is running."""
        svc = GenerationService(data_dir=str(tmp_path))
        status = await svc.wait_for_completion()
        assert status.state == GenerationState.IDLE

    @pytest.mark.asyncio
    async def test_wait_for_completion_waits_for_task(self, tmp_path, mock_logger):
        """wait_for_completion blocks until the generation task completes."""
        svc = GenerationService(data_dir=str(tmp_path))
        with patch.object(
            svc,
            "_sync_generate",
            return_value={
                "recipes": [{"id": 1, "name": "Test"}],
                "generated_at": "2024-01-01T00:00:00",
                "requested_count": 1,
                "constraint_count": 0,
                "status": "optimal",
                "warnings": [],
                "relaxed_constraints": [],
            },
        ):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            status = await svc.wait_for_completion(timeout=5.0)
        assert status.state == GenerationState.COMPLETE

    @pytest.mark.asyncio
    async def test_shutdown_when_idle(self, tmp_path):
        """shutdown does nothing when no task is running."""
        svc = GenerationService(data_dir=str(tmp_path))
        await svc.shutdown()
        assert svc.get_status().state == GenerationState.IDLE

    @pytest.mark.asyncio
    async def test_shutdown_cancels_running_task(self, tmp_path, mock_logger):
        """shutdown cancels an in-flight generation and resets state to IDLE."""
        svc = GenerationService(data_dir=str(tmp_path))

        # Use a slow sync_generate to ensure the task is still running
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)

        with patch.object(svc, "_run_generation", side_effect=slow_generate):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            assert svc.get_status().state == GenerationState.GENERATING
            await svc.shutdown(timeout=2.0)
        assert svc.get_status().state == GenerationState.IDLE

    def test_cleanup_stale_temp_files(self, tmp_path):
        """Stale .tmp files are removed on init."""
        (tmp_path / "menu.tmp").write_text("stale")
        (tmp_path / "current_menu.json").write_text('{"recipes": []}')
        GenerationService(data_dir=str(tmp_path))
        assert not (tmp_path / "menu.tmp").exists()
        assert (tmp_path / "current_menu.json").exists()

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, tmp_path, mock_logger):
        """wait_for_completion raises TimeoutError when task exceeds timeout."""
        svc = GenerationService(data_dir=str(tmp_path))

        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)

        with patch.object(svc, "_run_generation", side_effect=slow_generate):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            with pytest.raises(asyncio.TimeoutError):
                await svc.wait_for_completion(timeout=0.1)
        # Clean up — cancel the lingering task
        await svc.shutdown(timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_for_completion_after_error(self, tmp_path, mock_logger):
        """wait_for_completion returns ERROR status after a failed generation."""
        svc = GenerationService(data_dir=str(tmp_path))

        with patch.object(svc, "_sync_generate", side_effect=RuntimeError("solver exploded")):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            status = await svc.wait_for_completion(timeout=5.0)
        assert status.state == GenerationState.ERROR
        assert "solver exploded" in status.error

    @pytest.mark.asyncio
    async def test_shutdown_double_call(self, tmp_path):
        """Calling shutdown twice is safe (idempotent)."""
        svc = GenerationService(data_dir=str(tmp_path))
        await svc.shutdown()
        await svc.shutdown()
        assert svc.get_status().state == GenerationState.IDLE

    @pytest.mark.asyncio
    async def test_shutdown_after_error(self, tmp_path, mock_logger):
        """Shutdown after an error resets state to IDLE."""
        svc = GenerationService(data_dir=str(tmp_path))

        with patch.object(svc, "_sync_generate", side_effect=RuntimeError("boom")):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            # Wait for error state
            await svc.wait_for_completion(timeout=5.0)
            assert svc.get_status().state == GenerationState.ERROR

        # Shutdown should be safe even in ERROR state (task is already done)
        await svc.shutdown()
        # State remains ERROR because shutdown only resets IDLE when it cancels a running task
        # The task already completed (with error), so shutdown is a no-op
        assert svc.get_status().state == GenerationState.ERROR

    @pytest.mark.asyncio
    async def test_shutdown_immediately_after_start(self, tmp_path, mock_logger):
        """Shutdown right after start_generation cancels the task."""
        svc = GenerationService(data_dir=str(tmp_path))

        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)

        with patch.object(svc, "_run_generation", side_effect=slow_generate):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            # Immediately shut down — task should still be running
            await svc.shutdown(timeout=2.0)
        assert svc.get_status().state == GenerationState.IDLE
