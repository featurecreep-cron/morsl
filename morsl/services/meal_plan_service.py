from __future__ import annotations

import logging
from typing import Any, Dict, List

from morsl.tandoor_api import TandoorAPI


class MealPlanService:
    """Encapsulates meal-plan operations (scheduler + customer POST)."""

    def __init__(self, url: str, token: str, logger: logging.Logger) -> None:
        self._api = TandoorAPI(url, token, logger)
        self._logger = logger

    def cleanup(self, meal_plan_type: int, days: int) -> None:
        """Delete old uncooked meal plans (scheduler path)."""
        self._api.cleanup_uncooked_meal_plans(meal_plan_type=meal_plan_type, days=days)

    def create_from_menu(
        self, meal_plan_type_id: int, recipes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create meal plans for today from menu recipes (scheduler path)."""
        return self._api.create_meal_plans_from_menu(
            meal_plan_type_id=meal_plan_type_id,
            recipes=recipes,
        )

    def save_menu(
        self,
        meal_plan_type_id: int,
        recipes: List[Dict[str, Any]],
        date: str,
        shared: List[int],
    ) -> Dict[str, Any]:
        """Create meal plans with custom date + shared users (customer POST path).

        Returns {created, errors, total}.
        """
        return self._api.create_meal_plans_from_menu(
            meal_plan_type_id=meal_plan_type_id,
            recipes=recipes,
            date=date,
            shared=shared,
        )

    def save_weekly_plan(
        self,
        weekly_plan: Dict[str, Any],
        shared: List[int],
    ) -> Dict[str, Any]:
        """Save a weekly plan to Tandoor as meal plans.

        Iterates all days/meals and creates meal plan entries.
        Returns {created, errors, total}.
        """
        total_created = 0
        all_errors: List[str] = []
        total_recipes = 0

        for date_str, day_data in weekly_plan.get("days", {}).items():
            for mt_id_str, meal_data in day_data.get("meals", {}).items():
                recipes = meal_data.get("recipes", [])
                if not recipes:
                    continue
                total_recipes += len(recipes)
                result = self._api.create_meal_plans_from_menu(
                    meal_plan_type_id=int(mt_id_str),
                    recipes=recipes,
                    date=date_str,
                    shared=shared,
                )
                total_created += result.get("created", 0)
                all_errors.extend(result.get("errors", []))

        return {"created": total_created, "errors": all_errors, "total": total_recipes}
