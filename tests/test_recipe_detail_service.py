"""Tests for recipe detail fetching and ingredient extraction."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from morsl.services.recipe_detail_service import (
    _extract_steps_and_ingredients,
    _resolve_food,
    fetch_recipe_details,
)


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    return provider


def _make_recipe_obj(id=1, name="Test"):
    r = MagicMock()
    r.id = id
    r.name = name
    r.description = "Desc"
    r.rating = 4.0
    r.keywords = [10]
    r.keyword_names = {10: "Italian"}
    return r


class TestResolveFood:
    def test_returns_food_when_already_onhand(self, mock_provider, mock_logger):
        food = {"id": 1, "name": "Lime", "food_onhand": True}
        result = _resolve_food(mock_provider, food, mock_logger)
        assert result["name"] == "Lime"
        mock_provider.get_ingredient_substitutes.assert_not_called()

    def test_substitutes_when_available(self, mock_provider, mock_logger):
        food = {"id": 1, "name": "Lime", "food_onhand": False}
        mock_provider.get_ingredient_substitutes.return_value = [{"id": 2}]
        mock_provider.get_ingredient.return_value = {"id": 2, "name": "Lemon"}

        result = _resolve_food(mock_provider, food, mock_logger)
        assert result["name"] == "Lemon"

    def test_keeps_original_when_no_subs(self, mock_provider, mock_logger):
        food = {"id": 1, "name": "Lime", "food_onhand": False}
        mock_provider.get_ingredient_substitutes.return_value = []

        result = _resolve_food(mock_provider, food, mock_logger)
        assert result["name"] == "Lime"

    def test_keeps_original_on_api_error(self, mock_provider, mock_logger):
        food = {"id": 1, "name": "Lime", "food_onhand": False}
        mock_provider.get_ingredient_substitutes.side_effect = OSError("timeout")

        result = _resolve_food(mock_provider, food, mock_logger)
        assert result["name"] == "Lime"


class TestExtractStepsAndIngredients:
    def test_extracts_ingredients_and_steps(self, mock_provider, mock_logger):
        details = {
            "steps": [
                {
                    "ingredients": [
                        {
                            "food": {"id": 1, "name": "Flour", "food_onhand": True},
                            "amount": 2.0,
                            "unit": {"name": "cups"},
                        }
                    ],
                    "instruction": "Mix the flour.",
                    "name": "Step 1",
                    "time": 5,
                    "order": 0,
                }
            ]
        }

        ingredients, steps = _extract_steps_and_ingredients(mock_provider, details, mock_logger)
        assert len(ingredients) == 1
        assert ingredients[0]["food"] == "Flour"
        assert ingredients[0]["amount"] == 2.0
        assert ingredients[0]["unit"] == "cups"
        assert len(steps) == 1
        assert steps[0]["instruction"] == "Mix the flour."

    def test_skips_ingredients_without_food_name(self, mock_provider, mock_logger):
        details = {
            "steps": [
                {
                    "ingredients": [
                        {"food": None, "amount": 1.0},
                        {"food": {"id": 1}, "amount": 1.0},  # no name
                    ],
                    "instruction": "Do something.",
                }
            ]
        }
        ingredients, _steps = _extract_steps_and_ingredients(
            mock_provider,
            details,
            mock_logger,
        )
        assert len(ingredients) == 0

    def test_skips_empty_instructions(self, mock_provider, mock_logger):
        details = {
            "steps": [
                {"ingredients": [], "instruction": ""},
                {"ingredients": [], "instruction": "   "},
            ]
        }
        _ingredients, steps = _extract_steps_and_ingredients(
            mock_provider,
            details,
            mock_logger,
        )
        assert len(steps) == 0

    def test_handles_no_unit(self, mock_provider, mock_logger):
        details = {
            "steps": [
                {
                    "ingredients": [
                        {
                            "food": {"id": 1, "name": "Salt", "food_onhand": True},
                            "amount": 1.0,
                            "unit": None,
                        }
                    ],
                    "instruction": "Add salt.",
                }
            ]
        }
        ingredients, _ = _extract_steps_and_ingredients(mock_provider, details, mock_logger)
        assert ingredients[0]["unit"] is None


class TestFetchRecipeDetails:
    def test_fetches_details_for_each_recipe(self, mock_provider, mock_logger):
        r1 = _make_recipe_obj(1, "Pasta")
        r2 = _make_recipe_obj(2, "Pizza")

        mock_provider.get_recipe_details.return_value = {
            "image": "http://img.jpg",
            "working_time": 10,
            "cooking_time": 20,
            "keywords": [{"id": 10, "name": "Italian"}],
            "steps": [],
        }

        results = fetch_recipe_details(mock_provider, [r1, r2], mock_logger)
        assert len(results) == 2
        assert results[0]["name"] == "Pasta"
        assert results[0]["image"] == "http://img.jpg"
        assert results[1]["name"] == "Pizza"

    def test_handles_api_error_gracefully(self, mock_provider, mock_logger):
        from morsl.tandoor_api import TandoorError

        r1 = _make_recipe_obj(1, "Broken")
        mock_provider.get_recipe_details.side_effect = TandoorError("fail")

        results = fetch_recipe_details(mock_provider, [r1], mock_logger)
        assert len(results) == 1
        assert results[0]["name"] == "Broken"
        assert results[0]["image"] is None  # fallback
        assert results[0]["ingredients"] == []
