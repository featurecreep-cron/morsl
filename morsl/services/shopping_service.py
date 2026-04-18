"""Shopping list generation from menu recipes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from morsl.providers.base import RecipeProvider


# Conversion factors to a canonical unit within each measurement system.
# key = unit name (lowercase), value = (canonical_unit, multiplier)
_UNIT_CONVERSIONS: Dict[str, Tuple[str, float]] = {
    # Weight
    "g": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
    "kilograms": ("g", 1000.0),
    # Volume (metric)
    "ml": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "milliliters": ("ml", 1.0),
    "millilitre": ("ml", 1.0),
    "millilitres": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
    "liters": ("ml", 1000.0),
    "litre": ("ml", 1000.0),
    "litres": ("ml", 1000.0),
    # Volume (imperial) — keep as-is, don't cross-convert with metric
    "tsp": ("tsp", 1.0),
    "teaspoon": ("tsp", 1.0),
    "teaspoons": ("tsp", 1.0),
    "tbsp": ("tbsp", 1.0),
    "tablespoon": ("tbsp", 1.0),
    "tablespoons": ("tbsp", 1.0),
    "cup": ("cup", 1.0),
    "cups": ("cup", 1.0),
    "oz": ("oz", 1.0),
    "ounce": ("oz", 1.0),
    "ounces": ("oz", 1.0),
    "lb": ("lb", 1.0),
    "lbs": ("lb", 1.0),
    "pound": ("lb", 1.0),
    "pounds": ("lb", 1.0),
}

# When displaying, prefer human-friendly units above thresholds.
_DISPLAY_UPSCALE: Dict[str, Tuple[str, float, float]] = {
    # canonical_unit → (display_unit, threshold, divisor)
    "g": ("kg", 1000.0, 1000.0),
    "ml": ("l", 1000.0, 1000.0),
}


def _normalize_unit(unit: Optional[str]) -> Tuple[Optional[str], float]:
    """Return (canonical_unit, multiplier) for a unit string.

    If the unit is not recognized, returns (original, 1.0) so amounts
    are kept but won't merge with other unit variants.
    """
    if unit is None:
        return (None, 1.0)
    lookup = unit.strip().lower()
    if lookup in _UNIT_CONVERSIONS:
        return _UNIT_CONVERSIONS[lookup]
    return (unit, 1.0)


def _display_amount_unit(
    amount: Optional[float], canonical_unit: Optional[str]
) -> Tuple[Optional[float], Optional[str]]:
    """Upscale canonical units for display (e.g. 1500g → 1.5kg)."""
    if amount is None or canonical_unit is None:
        return amount, canonical_unit
    rule = _DISPLAY_UPSCALE.get(canonical_unit)
    if rule and amount >= rule[1]:
        return round(amount / rule[2], 2), rule[0]
    if amount == int(amount):
        return int(amount), canonical_unit
    return round(amount, 2), canonical_unit


class ShoppingItem:
    """A single item on the shopping list."""

    __slots__ = ("amount", "food", "source_recipes", "unit")

    def __init__(
        self,
        food: str,
        amount: Optional[float],
        unit: Optional[str],
        source_recipes: Optional[List[str]] = None,
    ) -> None:
        self.food = food
        self.amount = amount
        self.unit = unit
        self.source_recipes = source_recipes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food": self.food,
            "amount": self.amount,
            "unit": self.unit,
            "source_recipes": self.source_recipes,
        }


class ShoppingList:
    """Aggregated shopping list with source tracking."""

    __slots__ = ("items",)

    def __init__(self, items: Optional[List[ShoppingItem]] = None) -> None:
        self.items = items or []

    def to_dict(self) -> Dict[str, Any]:
        return {"items": [item.to_dict() for item in self.items]}

    def to_text(self) -> str:
        """Plain text shopping list for clipboard copy."""
        lines = []
        for item in self.items:
            if item.amount is not None and item.unit:
                lines.append(f"{item.amount} {item.unit} {item.food}")
            elif item.amount is not None:
                lines.append(f"{item.amount} {item.food}")
            else:
                lines.append(item.food)
        return "\n".join(lines)


def generate_shopping_list(
    recipes: List[Dict[str, Any]],
    exclude_onhand: Optional[List[str]] = None,
) -> ShoppingList:
    """Aggregate ingredients from recipe dicts into a deduplicated shopping list.

    Each recipe dict is expected to have:
      - name: str
      - ingredients: list of {food: str, amount: float|None, unit: str|None}

    Args:
        recipes: List of recipe dicts from current menu.
        exclude_onhand: List of on-hand food names to exclude (case-insensitive).
    """
    onhand_set = {name.lower() for name in (exclude_onhand or [])}

    # Group by (food_key, canonical_unit) → accumulated amount + source recipes
    # food_key is lowercase food name for dedup
    accumulator: Dict[Tuple[str, Optional[str]], Tuple[Optional[float], List[str], str]] = {}

    for recipe in recipes:
        recipe_name = recipe.get("name", "")
        for ing in recipe.get("ingredients", []):
            food_name = ing.get("food", "")
            if not food_name:
                continue

            food_key = food_name.lower()
            if food_key in onhand_set:
                continue
            amount = ing.get("amount")
            raw_unit = ing.get("unit")
            canonical_unit, multiplier = _normalize_unit(raw_unit)

            key = (food_key, canonical_unit)

            if key in accumulator:
                existing_amount, sources, display_name = accumulator[key]
                if amount is not None and existing_amount is not None:
                    accumulator[key] = (
                        existing_amount + amount * multiplier,
                        sources if recipe_name in sources else [*sources, recipe_name],
                        display_name,
                    )
                elif amount is not None:
                    accumulator[key] = (
                        amount * multiplier,
                        sources if recipe_name in sources else [*sources, recipe_name],
                        display_name,
                    )
                else:
                    accumulator[key] = (
                        existing_amount,
                        sources if recipe_name in sources else [*sources, recipe_name],
                        display_name,
                    )
            else:
                converted = amount * multiplier if amount is not None else None
                accumulator[key] = (converted, [recipe_name], food_name)

    # Build items sorted alphabetically by food name
    items = []
    for (_food_key, canonical_unit), (total, sources, display_name) in sorted(
        accumulator.items(), key=lambda x: x[0][0]
    ):
        display_amount, display_unit = _display_amount_unit(total, canonical_unit)
        items.append(
            ShoppingItem(
                food=display_name,
                amount=display_amount,
                unit=display_unit,
                source_recipes=sources,
            )
        )

    return ShoppingList(items=items)


def get_onhand_names(provider: RecipeProvider) -> List[str]:
    """Return food names currently marked as on-hand."""
    from morsl.providers.base import Capability

    if not (provider.capabilities() & Capability.ONHAND):
        return []
    return [f.get("name", "") for f in provider.get_onhand_items()]
