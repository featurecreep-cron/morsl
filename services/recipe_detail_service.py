"""Shared recipe detail fetching — used by GenerationService and WeeklyGenerationService."""
from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import Any, Dict, List

from tandoor_api import TandoorAPI


def fetch_recipe_details(
    api: TandoorAPI,
    recipes: list,
    logger: Logger,
) -> List[Dict[str, Any]]:
    """Fetch full details (image, ingredients, steps) for a list of Recipe objects.

    Uses a thread pool for parallel API calls. Each recipe gets on-hand
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
            "keywords": [{"id": kid, "name": getattr(r, 'keyword_names', {}).get(kid, "")} for kid in r.keywords],
            "steps": [],
            "working_time": None,
            "cooking_time": None,
        }
        try:
            details = api.get_recipe_details(r.id)
            recipe_data["image"] = details.get("image")
            recipe_data["working_time"] = details.get("working_time")
            recipe_data["cooking_time"] = details.get("cooking_time")
            # Enrich keywords with names from detailed response
            detail_kws = details.get("keywords", [])
            if detail_kws:
                recipe_data["keywords"] = [{"id": kw["id"], "name": kw.get("name", "")} for kw in detail_kws]
            for step in details.get("steps", []):
                for ing in step.get("ingredients", []):
                    food_obj = ing.get("food")
                    if not food_obj or not food_obj.get("name"):
                        continue
                    # On-hand substitution: if food is not on hand,
                    # try to find an on-hand substitute
                    if not food_obj.get("food_onhand"):
                        try:
                            subs = api.get_food_substitutes(food_obj["id"], substitute="food")
                            if subs:
                                food_obj = api.get_food(random.choice(subs)["id"])
                        except (KeyError, IndexError, TypeError) as e:
                            logger.debug(f"Substitute lookup failed for food {food_obj.get('id')}: {e}")
                        except Exception as e:
                            logger.warning(f"Unexpected error in substitute lookup for food {food_obj.get('id')}: {e}")
                    recipe_data["ingredients"].append({
                        "amount": ing.get("amount"),
                        "unit": ing.get("unit", {}).get("name") if ing.get("unit") else None,
                        "food": food_obj["name"],
                    })
                instruction = step.get("instruction", "").strip()
                if instruction:
                    recipe_data["steps"].append({
                        "name": step.get("name", ""),
                        "instruction": instruction,
                        "time": step.get("time", 0),
                        "order": step.get("order", 0),
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch details for recipe {r.id}: {e}")
        return recipe_data

    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(_fetch_one, recipes))
