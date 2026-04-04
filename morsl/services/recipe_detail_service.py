"""Shared recipe detail fetching — used by GenerationService and WeeklyGenerationService."""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import Any, Dict, List

from morsl.tandoor_api import TandoorAPI, TandoorError

# Module-level shared pool — avoids recreating threads on every generation
_detail_pool = ThreadPoolExecutor(max_workers=10)


def _resolve_food(api: TandoorAPI, food_obj: dict, logger: Logger) -> dict:
    """Resolve on-hand food substitution for a single ingredient."""
    if food_obj.get("food_onhand"):
        return food_obj
    try:
        subs = api.get_food_substitutes(food_obj["id"], substitute="food")
        if subs:
            return api.get_food(random.choice(subs)["id"])
    except (KeyError, IndexError, TypeError) as e:
        logger.debug("Substitute lookup failed for food %s: %s", food_obj.get("id"), e)
    except OSError as e:  # RequestException inherits IOError/OSError
        logger.warning(
            "Unexpected error in substitute lookup for food %s: %s", food_obj.get("id"), e
        )
    return food_obj


def _batch_resolve_foods(api: TandoorAPI, food_objs: list[dict], logger: Logger) -> list[dict]:
    """Resolve substitutions for a batch of foods using the shared thread pool.

    Parallelises the per-ingredient substitute lookups that were previously
    sequential within each recipe.
    """
    # Split into on-hand (no lookup needed) and off-hand (need substitute check)
    indexed: list[tuple[int, dict]] = []
    results: list[dict] = list(food_objs)  # shallow copy — positions preserved
    for i, food in enumerate(food_objs):
        if not food.get("food_onhand"):
            indexed.append((i, food))

    if not indexed:
        return results

    def _resolve(item: tuple[int, dict]) -> tuple[int, dict]:
        _, food = item
        return item[0], _resolve_food(api, food, logger)

    futures = _detail_pool.map(_resolve, indexed)
    for idx, resolved in futures:
        results[idx] = resolved

    return results


def _extract_steps_and_ingredients(
    api: TandoorAPI, details: dict, logger: Logger
) -> tuple[list, list]:
    """Extract ingredients and steps from a Tandoor recipe details response."""
    raw_foods: list[dict] = []
    raw_ings: list[dict] = []
    steps = []
    for step in details.get("steps", []):
        for ing in step.get("ingredients", []):
            food_obj = ing.get("food")
            if not food_obj or not food_obj.get("name"):
                continue
            raw_foods.append(food_obj)
            raw_ings.append(ing)
        instruction = step.get("instruction", "").strip()
        if instruction:
            steps.append(
                {
                    "name": step.get("name", ""),
                    "instruction": instruction,
                    "time": step.get("time", 0),
                    "order": step.get("order", 0),
                }
            )

    # Batch-resolve all food substitutions for this recipe
    resolved_foods = _batch_resolve_foods(api, raw_foods, logger)

    ingredients = []
    for ing, food_obj in zip(raw_ings, resolved_foods, strict=True):
        ingredients.append(
            {
                "amount": ing.get("amount"),
                "unit": ing.get("unit", {}).get("name") if ing.get("unit") else None,
                "food": food_obj["name"],
            }
        )
    return ingredients, steps


def fetch_recipe_details(
    api: TandoorAPI,
    recipes: tuple | list,
    logger: Logger,
) -> List[Dict[str, Any]]:
    """Fetch full details (image, ingredients, steps) for a list of Recipe objects.

    Uses a shared thread pool for parallel API calls. Each recipe gets on-hand
    food substitution when available.
    """

    def _fetch_one(r) -> Dict[str, Any]:
        recipe_data: Dict[str, Any] = {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rating": r.rating,
            "image": None,
            "ingredients": [],
            "keywords": [
                {"id": kid, "name": getattr(r, "keyword_names", {}).get(kid, "")}
                for kid in r.keywords
            ],
            "steps": [],
            "working_time": None,
            "cooking_time": None,
        }
        try:
            details = api.get_recipe_details(r.id)
            recipe_data["image"] = details.get("image")
            recipe_data["working_time"] = details.get("working_time")
            recipe_data["cooking_time"] = details.get("cooking_time")
            detail_kws = details.get("keywords", [])
            if detail_kws:
                recipe_data["keywords"] = [
                    {"id": kw["id"], "name": kw.get("name", "")} for kw in detail_kws
                ]
            recipe_data["ingredients"], recipe_data["steps"] = _extract_steps_and_ingredients(
                api, details, logger
            )
        except (TandoorError, KeyError, ValueError) as e:
            logger.warning("Failed to fetch details for recipe %s: %s", r.id, e)
        return recipe_data

    return list(_detail_pool.map(_fetch_one, recipes))
