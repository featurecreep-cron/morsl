from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import Any, Dict, List, Optional

from morsl.constants import API_CACHE_TTL_MINUTES, DEFAULT_CHOICES
from morsl.models import (
    Book,
    Food,
    Recipe,
    SolverResult,
    make_book,
    make_food,
    make_keyword,
    make_recipe,
)
from morsl.solver import RecipePicker
from morsl.tandoor_api import TandoorAPI, TandoorError
from morsl.utils import format_date


def _build_rating_condition(c: Dict[str, Any]):
    """Build a rating filter condition from constraint dict."""
    min_rating = c.get("min")
    max_rating = c.get("max")
    if c.get("unrated", False):
        return 0
    if min_rating is not None and max_rating is not None:
        return [min_rating, max_rating]
    if min_rating is not None:
        return min_rating
    if max_rating is not None:
        return -max_rating  # negative means "at most"
    return None


def _resolve_date_recipes(recipes, c: Dict[str, Any], date_field: str) -> list:
    """Resolve recipes matching a within_days/older_than_days date constraint."""
    within_days = c.get("within_days")
    older_than_days = c.get("older_than_days")
    if within_days is not None:
        d, _ = format_date(f"{within_days}d")
        return Recipe.recipes_with_date(recipes, date_field, d, after=True)
    if older_than_days is not None:
        d, _ = format_date(f"-{older_than_days}d")
        return Recipe.recipes_with_date(recipes, date_field, d, after=False)
    return list(recipes)


def _apply_date_filters(recipes: List[Recipe], constraint: Dict[str, Any]) -> List[Recipe]:
    """Apply cooked_date and created_date filters from a parsed constraint."""
    if cooked_date := constraint.get("cooked_date"):
        recipes = Recipe.recipes_with_date(
            recipes, "cookedon", cooked_date, after=constraint.get("cooked_after", False)
        )
    if created_date := constraint.get("created_date"):
        recipes = Recipe.recipes_with_date(
            recipes, "createdon", created_date, after=constraint.get("created_after", False)
        )
    return recipes


class MenuService:
    """Core business logic for menu generation.

    Accepts plain Python types so both CLI and API can use it.
    Uses v2 profile format with unified constraints array.
    """

    def __init__(
        self,
        url: str,
        token: str,
        config: Dict[str, Any],
        logger: Logger,
        api: Optional[TandoorAPI] = None,
    ) -> None:
        self.logger = logger
        self.config = config
        self.include_children: bool = config.get("include_children", True)
        self.choices: int = int(config.get("choices", DEFAULT_CHOICES))
        self.min_choices: Optional[int] = (
            int(config["min_choices"]) if config.get("min_choices") else None
        )
        self.cache: int = int(config.get("cache", API_CACHE_TTL_MINUTES))

        self.tandoor = api or TandoorAPI(url, token, self.logger, cache=self.cache)
        self.recipes: List[Recipe] = []
        self.recipe_picker: Optional[RecipePicker] = None

        # Parse unified constraints array (v2 format)
        self.constraints: List[Dict[str, Any]] = self._parse_constraints(
            config.get("constraints", [])
        )

    def _parse_constraints(self, raw: List[Any]) -> List[Dict[str, Any]]:
        """Parse v2 constraints array."""
        parsed: List[Dict[str, Any]] = []
        for item in raw:
            constraint = dict(item)
            constraint["count"] = int(constraint.get("count", 0))

            # Extract item IDs from items array
            if "items" in constraint:
                constraint["item_ids"] = [i["id"] for i in constraint["items"]]
            if "except" in constraint:
                constraint["except_ids"] = [i["id"] for i in constraint["except"]]

            # Parse date filters
            # older_than_days: recipes with date BEFORE cutoff (after=False)
            # within_days: recipes with date AFTER cutoff (after=True)
            if cooked := constraint.get("cooked"):
                if "older_than_days" in cooked:
                    constraint["cooked_date"], _ = format_date(f"-{cooked['older_than_days']}days")
                    constraint["cooked_after"] = False
                elif "within_days" in cooked:
                    constraint["cooked_date"], _ = format_date(f"{cooked['within_days']}days")
                    constraint["cooked_after"] = True

            if created := constraint.get("created"):
                if "older_than_days" in created:
                    constraint["created_date"], _ = format_date(
                        f"-{created['older_than_days']}days"
                    )
                    constraint["created_after"] = False
                elif "within_days" in created:
                    constraint["created_date"], _ = format_date(f"{created['within_days']}days")
                    constraint["created_after"] = True

            parsed.append(constraint)
        return parsed

    def prepare_recipes(self) -> None:
        """Load recipe pool from Tandoor API."""
        recipes_param = self.config.get("recipes")
        filters_param = self.config.get("filters", [])
        plan_type = self.config.get("plan_type", [])

        if not recipes_param and not filters_param and not plan_type:
            for r in self.tandoor.get_recipes(all_recipes=True):
                self.recipes.append(make_recipe(r))
        else:
            for r in self.tandoor.get_recipes(params=recipes_param, filters=filters_param):
                self.recipes.append(make_recipe(r))
            mp_date = self.config.get("mp_date")
            for r in self.tandoor.get_mealplan_recipes(
                mealtype_id=plan_type, date=mp_date, params=recipes_param
            ):
                self.recipes.append(make_recipe(r))
        self.recipes = list(dict.fromkeys(self.recipes))
        self._recipe_set = frozenset(self.recipes)

    def prepare_constraints(self) -> None:
        """Prepare all constraints by fetching related data from API."""
        for constraint in self.constraints:
            ctype = constraint.get("type")

            if ctype == "keyword":
                self._prepare_keyword_constraint(constraint)
            elif ctype == "food":
                self._prepare_food_constraint(constraint)
            elif ctype == "book":
                self._prepare_book_constraint(constraint)
            elif ctype == "makenow":
                self._prepare_makenow_constraint(constraint)
            # rating, cookedon, createdon don't need API prep

    def _prepare_keyword_constraint(self, constraint: Dict[str, Any]) -> None:
        """Fetch keyword tree and resolve to Keyword objects."""
        item_ids = constraint.get("item_ids", [])
        include_children = constraint.get("include_children", self.include_children)

        kw_tree: List[Dict[str, Any]] = []
        if len(item_ids) <= 1:
            for kw_id in item_ids:
                if include_children:
                    kw_tree += self.tandoor.get_keyword_tree(kw_id)
                else:
                    kw_tree.append(self.tandoor.get_keyword(kw_id))
        else:
            fetch = self.tandoor.get_keyword_tree if include_children else self.tandoor.get_keyword
            with ThreadPoolExecutor(max_workers=len(item_ids)) as pool:
                results = pool.map(fetch, item_ids)
                for result in results:
                    if isinstance(result, list):
                        kw_tree += result
                    else:
                        kw_tree.append(result)

        constraint["keywords"] = list({make_keyword(k) for k in kw_tree})

    def _prepare_food_constraint(self, constraint: Dict[str, Any]) -> None:
        """Fetch food data and find matching recipes."""
        item_ids = constraint.get("item_ids", [])
        except_ids = constraint.get("except_ids", [])

        # Fetch Food objects for logging — skip items that fail
        food_list: List[Food] = []
        if len(item_ids) <= 1:
            for fd_id in item_ids:
                try:
                    food_list.append(make_food(self.tandoor.get_food(fd_id)))
                except TandoorError:
                    self.logger.warning(f"Failed to fetch food {fd_id}, skipping")
        else:

            def _fetch_food(fd_id):
                try:
                    return make_food(self.tandoor.get_food(fd_id))
                except TandoorError:
                    self.logger.warning(f"Failed to fetch food {fd_id}, skipping")
                    return None

            with ThreadPoolExecutor(max_workers=len(item_ids)) as pool:
                for food in pool.map(_fetch_food, item_ids):
                    if food is not None:
                        food_list.append(food)
        constraint["foods"] = food_list

        # Find recipes with these foods
        params: Dict[str, List[int]] = {"foods_or": item_ids, "foods_or_not": except_ids}
        found_recipes: List[Recipe] = []
        for r in self.tandoor.get_recipes(params=params):
            found_recipes.append(make_recipe(r))

        self.logger.info(
            f"Food constraint {[f.name for f in food_list]}: {len(found_recipes)} recipes found"
        )

        constraint["matching_recipes"] = _apply_date_filters(found_recipes, constraint)

    def _prepare_book_constraint(self, constraint: Dict[str, Any]) -> None:
        """Fetch book data and find matching recipes."""
        item_ids = constraint.get("item_ids", [])

        book_list: List[Book] = []
        for bk_id in item_ids:
            book_list.append(make_book(self.tandoor.get_book(bk_id)))
        constraint["books"] = book_list

        found_recipes: List[Recipe] = []
        for bk in book_list:
            for r in self.tandoor.get_book_recipes(bk):
                found_recipes.append(make_recipe(r))

        constraint["matching_recipes"] = _apply_date_filters(found_recipes, constraint)

    def prepare_data(self) -> None:
        """Prepare all data needed for solving."""
        self.prepare_recipes()
        self.prepare_constraints()

    def _apply_keyword_constraint(self, c, exclude, weight) -> None:
        found = Recipe.recipes_with_keyword(self.recipes, c.get("keywords", []))
        found = _apply_date_filters(found, c)
        self.recipe_picker.add_keyword_constraint(
            found,
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def _apply_food_constraint(self, c, exclude, weight) -> None:
        self.recipe_picker.add_food_constraint(
            c.get("matching_recipes", []),
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def _apply_book_constraint(self, c, exclude, weight) -> None:
        self.recipe_picker.add_book_constraint(
            c.get("matching_recipes", []),
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def _prepare_makenow_constraint(self, constraint: Dict[str, Any]) -> None:
        """Fetch recipes that can be made with on-hand ingredients."""
        recipes = self.tandoor.get_recipes(params={"makenow": True})
        found = [make_recipe(r) for r in recipes]
        found = [r for r in found if r in self._recipe_set]
        found = _apply_date_filters(found, constraint)
        constraint["matching_recipes"] = found

    def _apply_makenow_constraint(self, c, exclude, weight) -> None:
        self.recipe_picker.add_book_constraint(
            c.get("matching_recipes", []),
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def _apply_rating_constraint(self, c, exclude, weight) -> None:
        found = _apply_date_filters(list(self.recipes), c)
        rating_condition = _build_rating_condition(c)
        found = Recipe.recipes_with_rating(found, rating_condition)
        self.recipe_picker.add_rating_constraints(
            found,
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def _apply_date_constraint(self, c, date_field, exclude, weight) -> None:
        found = _resolve_date_recipes(self.recipes, c, date_field)
        found = _apply_date_filters(found, c)
        adder = (
            self.recipe_picker.add_cookedon_constraints
            if date_field == "cookedon"
            else self.recipe_picker.add_createdon_constraints
        )
        adder(
            found,
            c["count"],
            c["operator"],
            exclude=exclude,
            weight=weight,
            upper_bound=c.get("upper_bound"),
        )

    def select_recipes(self) -> SolverResult:
        """Run the solver with all constraints."""
        self.recipe_picker = RecipePicker(
            self.recipes, self.choices, logger=self.logger, min_choices=self.min_choices
        )

        handlers = {
            "keyword": self._apply_keyword_constraint,
            "food": self._apply_food_constraint,
            "book": self._apply_book_constraint,
            "rating": self._apply_rating_constraint,
            "makenow": self._apply_makenow_constraint,
        }

        for c in self.constraints:
            ctype = c.get("type")
            exclude = c.get("exclude", False)
            soft = c.get("soft", False)
            weight = 1 if soft else int(c.get("weight", 0))

            if ctype in handlers:
                handlers[ctype](c, exclude, weight)
            elif ctype in ("cookedon", "createdon"):
                self._apply_date_constraint(c, ctype, exclude, weight)

        return self.recipe_picker.solve()
