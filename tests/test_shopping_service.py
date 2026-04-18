"""Tests for shopping list generation."""

from __future__ import annotations

from morsl.services.shopping_service import (
    ShoppingItem,
    ShoppingList,
    generate_shopping_list,
)


def _recipe(name, ingredients):
    return {"name": name, "ingredients": ingredients}


def _ing(food, amount=None, unit=None):
    return {"food": food, "amount": amount, "unit": unit}


class TestGenerateShoppingList:
    def test_empty_recipes(self):
        result = generate_shopping_list([])
        assert len(result.items) == 0

    def test_single_recipe_single_ingredient(self):
        recipes = [_recipe("Pasta", [_ing("flour", 2.0, "cup")])]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].food == "flour"
        assert result.items[0].amount == 2
        assert result.items[0].unit == "cup"
        assert result.items[0].source_recipes == ["Pasta"]

    def test_aggregates_same_food_same_unit(self):
        recipes = [
            _recipe("Pasta", [_ing("flour", 2.0, "cup")]),
            _recipe("Bread", [_ing("flour", 3.0, "cups")]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 5
        assert result.items[0].unit == "cup"
        assert set(result.items[0].source_recipes) == {"Pasta", "Bread"}

    def test_different_units_kept_separate(self):
        recipes = [
            _recipe("A", [_ing("butter", 2.0, "tbsp")]),
            _recipe("B", [_ing("butter", 100.0, "g")]),
        ]
        result = generate_shopping_list(recipes)
        # Should have 2 separate entries for butter (tbsp and g)
        butter_items = [i for i in result.items if i.food.lower() == "butter"]
        assert len(butter_items) == 2

    def test_unit_normalization_grams_to_kg(self):
        recipes = [
            _recipe("A", [_ing("flour", 800.0, "g")]),
            _recipe("B", [_ing("flour", 500.0, "grams")]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 1.3
        assert result.items[0].unit == "kg"

    def test_unit_normalization_ml_to_l(self):
        recipes = [
            _recipe("A", [_ing("milk", 500.0, "ml")]),
            _recipe("B", [_ing("milk", 750.0, "milliliters")]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 1.25
        assert result.items[0].unit == "l"

    def test_stays_in_grams_below_threshold(self):
        recipes = [_recipe("A", [_ing("salt", 5.0, "g")])]
        result = generate_shopping_list(recipes)
        assert result.items[0].amount == 5
        assert result.items[0].unit == "g"

    def test_case_insensitive_food_dedup(self):
        recipes = [
            _recipe("A", [_ing("Flour", 1.0, "cup")]),
            _recipe("B", [_ing("flour", 2.0, "cup")]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 3

    def test_preserves_original_food_name_casing(self):
        """First occurrence's casing is preserved."""
        recipes = [_recipe("A", [_ing("Brown Sugar", 1.0, "cup")])]
        result = generate_shopping_list(recipes)
        assert result.items[0].food == "Brown Sugar"

    def test_no_unit_ingredient(self):
        recipes = [_recipe("A", [_ing("eggs", 3.0, None)])]
        result = generate_shopping_list(recipes)
        assert result.items[0].amount == 3
        assert result.items[0].unit is None

    def test_no_amount_ingredient(self):
        recipes = [_recipe("A", [_ing("salt", None, None)])]
        result = generate_shopping_list(recipes)
        assert result.items[0].amount is None
        assert result.items[0].unit is None

    def test_aggregates_no_unit_items(self):
        recipes = [
            _recipe("A", [_ing("eggs", 3.0, None)]),
            _recipe("B", [_ing("eggs", 2.0, None)]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 5

    def test_skips_empty_food_name(self):
        recipes = [_recipe("A", [_ing("", 1.0, "cup")])]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 0

    def test_sorted_alphabetically(self):
        recipes = [
            _recipe("A", [_ing("zucchini", 1.0, None), _ing("apple", 2.0, None)]),
        ]
        result = generate_shopping_list(recipes)
        assert result.items[0].food == "apple"
        assert result.items[1].food == "zucchini"

    def test_same_recipe_not_duplicated_in_sources(self):
        recipes = [
            _recipe(
                "Pasta",
                [
                    _ing("garlic", 2.0, "clove"),
                    _ing("garlic", 1.0, "clove"),
                ],
            ),
        ]
        result = generate_shopping_list(recipes)
        assert result.items[0].source_recipes == ["Pasta"]
        assert result.items[0].amount == 3

    def test_multiple_recipes_multiple_ingredients(self):
        recipes = [
            _recipe(
                "Pasta",
                [
                    _ing("flour", 2.0, "cup"),
                    _ing("eggs", 3.0, None),
                    _ing("salt", 1.0, "tsp"),
                ],
            ),
            _recipe(
                "Bread",
                [
                    _ing("flour", 4.0, "cup"),
                    _ing("yeast", 1.0, "tbsp"),
                    _ing("salt", 0.5, "tsp"),
                ],
            ),
        ]
        result = generate_shopping_list(recipes)
        foods = {i.food.lower(): i for i in result.items}
        assert foods["flour"].amount == 6
        assert foods["eggs"].amount == 3
        assert foods["salt"].amount == 1.5
        assert foods["yeast"].amount == 1

    def test_kg_input_merges_with_g(self):
        recipes = [
            _recipe("A", [_ing("chicken", 1.0, "kg")]),
            _recipe("B", [_ing("chicken", 500.0, "g")]),
        ]
        result = generate_shopping_list(recipes)
        assert len(result.items) == 1
        assert result.items[0].amount == 1.5
        assert result.items[0].unit == "kg"


class TestShoppingListText:
    def test_to_text_with_units(self):
        sl = ShoppingList(
            [
                ShoppingItem("flour", 2.0, "cup"),
                ShoppingItem("eggs", 3.0, None),
                ShoppingItem("salt", None, None),
            ]
        )
        text = sl.to_text()
        lines = text.split("\n")
        assert lines[0] == "2.0 cup flour"
        assert lines[1] == "3.0 eggs"
        assert lines[2] == "salt"

    def test_to_text_empty(self):
        sl = ShoppingList([])
        assert sl.to_text() == ""


class TestExcludeOnhand:
    def test_excludes_onhand_items(self):
        recipes = [
            _recipe(
                "A",
                [
                    _ing("flour", 2.0, "cup"),
                    _ing("butter", 1.0, "tbsp"),
                    _ing("eggs", 3.0, None),
                ],
            ),
        ]
        result = generate_shopping_list(recipes, exclude_onhand=["flour", "Eggs"])
        assert len(result.items) == 1
        assert result.items[0].food == "butter"

    def test_exclude_empty_list(self):
        recipes = [_recipe("A", [_ing("flour", 1.0, "cup")])]
        result = generate_shopping_list(recipes, exclude_onhand=[])
        assert len(result.items) == 1

    def test_exclude_none(self):
        recipes = [_recipe("A", [_ing("flour", 1.0, "cup")])]
        result = generate_shopping_list(recipes, exclude_onhand=None)
        assert len(result.items) == 1


class TestShoppingListDict:
    def test_to_dict(self):
        sl = ShoppingList([ShoppingItem("flour", 2.0, "cup", ["Pasta"])])
        d = sl.to_dict()
        assert len(d["items"]) == 1
        assert d["items"][0] == {
            "food": "flour",
            "amount": 2.0,
            "unit": "cup",
            "source_recipes": ["Pasta"],
        }
