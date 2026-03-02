from __future__ import annotations

import json
from datetime import datetime
from logging import Logger
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from constants import (
    API_CACHE_TTL_MINUTES,
    API_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    HTTP_BACKOFF_FACTOR,
    HTTP_MAX_RETRIES,
    HTTP_POOL_CONNECTIONS,
    HTTP_POOL_MAXSIZE,
    HTTP_RETRY_STATUS_CODES,
)
from utils import cached, now

if TYPE_CHECKING:
    from models import Book, Recipe


class TandoorError(Exception):
    """Base exception for Tandoor API errors."""


class TandoorConnectionError(TandoorError):
    """Raised when we cannot connect to the Tandoor server."""


class TandoorNotFoundError(TandoorError):
    """Raised when a requested resource is not found (404)."""


class TandoorAPIError(TandoorError):
    """Raised for non-success HTTP responses from Tandoor."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"Tandoor API error {status_code}: {detail}")


class TandoorAPI:
    def __init__(self, url: str, token: str, logger: Logger, **kwargs: Dict[str, Any]) -> None:
        self.logger = logger
        self.ttl = kwargs.get("cache", API_CACHE_TTL_MINUTES)
        self.token = token
        self.page_size = kwargs.get("page_size", API_PAGE_SIZE)
        self.include_children = kwargs.get("include_children", True)
        if url and url[-1] == "/":
            self.url = f"{url}api/"
        else:
            self.url = f"{url}/api/"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

        # Connection-pooled session with retries and default timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        adapter = HTTPAdapter(
            max_retries=Retry(total=HTTP_MAX_RETRIES, backoff_factor=HTTP_BACKOFF_FACTOR, status_forcelist=HTTP_RETRY_STATUS_CODES),
            pool_connections=HTTP_POOL_CONNECTIONS,
            pool_maxsize=HTTP_POOL_MAXSIZE,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @cached
    def get_paged_results(self, url: str, params: Optional[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        results = []
        while url:
            self.logger.debug(f"Connecting to tandoor api at url: {url}")
            self.logger.debug(f"Connecting with params: {params!s}")
            if "?" in url:
                params = None
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                self.logger.info(f"Failed to fetch recipes. Status code: {response.status_code}: {response.text}")
                raise TandoorAPIError(response.status_code, response.text)
            content = json.loads(response.content)
            new_results = content.get("results", [])
            self.logger.debug(f"Retrieved {len(new_results)} results.")
            results = results + new_results
            url = content.get("next", None)
        return results

    @cached
    def get_unpaged_results(self, url: str, obj_id: Union[str, int], **kwargs) -> Dict[str, Any]:
        url = f"{url}{obj_id}"
        self.logger.debug(f"Connecting to tandoor api at url: {url}")
        response = self.session.get(url, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 200:
            self.logger.info(f"Failed to fetch recipes. Status code: {response.status_code}: {response.text}")
            raise TandoorAPIError(response.status_code, response.text)
        return json.loads(response.content)

    def create_object(self, url: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self.logger.debug(f"Create object with tandoor api at url: {url}")
        response = self.session.post(url, json=data, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 201:
            return response.json()
        else:
            self.logger.info(f"Error creating object: {response.text}")
            raise RuntimeError(f"Error creating object: {response.text}")

    def delete_object(self, url: str, obj_id: Union[str, int], **kwargs) -> None:
        self.logger.debug(f"Deleting object with tandoor api at url: {url}")
        response = self.session.delete(f"{url}{obj_id}/", timeout=DEFAULT_TIMEOUT)

        if response.status_code != 204:
            self.logger.info(f"Error deleting object: {response.text}")
            raise RuntimeError(f"Error deleting object: {response.text}")

    def get_recipes(self, params: Optional[Dict[str, Any]] = None, filters: Union[List[int], int, None] = None, **kwargs) -> List[Dict[str, Any]]:
        """Fetch a list of recipes from the API.

        Two independent query paths run in sequence and results are concatenated:

        1. **params query** — runs when ``params`` is truthy or ``all_recipes=True``.
           Adds ``include_children`` and ``page_size`` to the params dict before querying.
        2. **filters query** — runs when ``filters is not None``.
           Each filter ID triggers a separate paged query with ``?filter=<id>``.

        Args:
            params: Tandoor recipe search parameters (e.g. ``foods_or``, ``keywords_or``).
                    ``None`` (default) skips the params query entirely.
            filters: CustomFilter ID(s). ``None`` (default) skips filter queries.
                     Pass ``[]`` explicitly to indicate "no filters" while still entering
                     the filter code path (though it will produce no results).
            **kwargs: Forwarded to ``get_paged_results``.  ``all_recipes=True`` forces the
                      params query to run even when ``params`` is ``None``.

        Returns:
            Combined list of recipe dicts from both query paths.
        """
        url = f"{self.url}recipe/"
        recipes: List[Dict[str, Any]] = []
        if params or kwargs.get("all_recipes", False):
            params = params or {}
            params["include_children"] = self.include_children
            params["page_size"] = self.page_size
            recipes = self.get_paged_results(url, params, **kwargs)

        if filters is not None:
            if not isinstance(filters, list):
                filters = [filters]
            for f in filters:
                recipes += self.get_paged_results(url, {"page_size": self.page_size, "filter": f})

        self.logger.debug(f"Returning {len(recipes)} total recipes.")
        return recipes

    @cached
    def get_recipe_details(self, recipe_id: Union[str, int]) -> Dict[str, Any]:
        """
        Fetch details of a specific recipe by its ID.
        Args:
            recipe_id (str): The ID of the recipe to retrieve.
        Returns:
            dict: Details of the recipe in JSON-LD format.
        """
        url = f"{self.url}recipe/{recipe_id}"
        response = self.session.get(url, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            return response.json()
        else:
            raise TandoorAPIError(response.status_code, response.text)

    def get_keyword_tree(self, kw_id: str | int, params: dict[str, Any] | None = None, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch a keyword and it's descendants from the API.
        Returns:
            list: A list of keyword objects in tandoor format.
        """

        url = f"{self.url}keyword/"
        params = params or {}
        params["tree"] = kw_id
        params["page_size"] = self.page_size
        keywords = self.get_paged_results(url, params, **kwargs)

        self.logger.debug(f"Returning {len(keywords)} total keywords.")
        return keywords

    def get_food_tree(self, food_id: Union[str, int], params: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch a food and it's descendants from the API.
        Returns:
            list: A list of food objects in tandoor format.
        """

        url = f"{self.url}food/"
        params = params or {}
        params["tree"] = food_id
        params["page_size"] = self.page_size
        foods = self.get_paged_results(url, params, **kwargs)

        self.logger.debug(f"Returning {len(foods)} total food.")
        return foods

    def get_food(self, food_id: Union[str, int], params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Fetch a single food by ID."""

        url = f"{self.url}food/"
        food = self.get_unpaged_results(url, food_id, **kwargs)

        self.logger.debug(f'Returning food {food["id"]}: {food["name"]}.')
        return food

    def get_book(self, book_id: Union[str, int], params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Fetch a single recipe book by ID."""

        url = f"{self.url}recipe-book/"
        book = self.get_unpaged_results(url, book_id, **kwargs)

        self.logger.debug(f'Returning book {book["id"]}: {book["name"]}.')
        return book

    @cached
    def get_book_recipes(self, book: "Book", params: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch all recipes in a book from the API.
        Returns:
            list: List of book contents.
        """

        url = f"{self.url}recipe-book-entry/?book={book.id}"
        book_entries = self.get_unpaged_results(url, "", **kwargs)
        recipes = [be["recipe_content"] for be in book_entries]
        if book.filter:
            recipes += self.get_recipes(filters=book.filter)

        self.logger.debug(f"Returning book {book.id}: {book.name} with {len(recipes)} recipes.")
        return recipes

    def get_mealplan_recipes(
        self, mealtype_id: Optional[Union[List[int], int]] = None, date: Optional[datetime] = None, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch all recipes of mealtype.
        Returns:
            list: List of recipes.
        """

        if not mealtype_id:
            return []
        if date is None:
            date = now()
        if not isinstance(mealtype_id, list):
            mealtype_id = [mealtype_id]

        url = f"{self.url}meal-plan/?from_date={date.strftime('%Y-%m-%d')}&to_date={date.strftime('%Y-%m-%d')}"
        for mt in mealtype_id:
            url = url + f"&meal_type={mt}"

        self.logger.debug(f"Returning recipes from meal plan on {date.strftime('%Y-%m-%d')} with meal play type IDs: {mealtype_id}.")
        return [r["recipe"] for r in self.get_unpaged_results(url, "", **kwargs)]

    def create_meal_plan(
        self,
        recipe: Optional["Recipe"] = None,
        title: Optional[str] = None,
        servings: int = 1,
        date: Optional[datetime] = None,
        note: Optional[str] = None,
        type: Optional[int] = None,
        shared: Optional[List[Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if date is None:
            date = now()
        url = f"{self.url}meal-plan/"
        plan = self.create_object(
            url,
            {
                "title": title,
                "recipe": {"id": recipe.id, "name": recipe.name, "keywords": []},
                "servings": servings,
                "note": note,
                "shared": shared,
                "from_date": date.strftime("%Y-%m-%d"),
                "to_date": date.strftime("%Y-%m-%d"),
                "meal_type": self.get_meal_type(type),
            },
        )

        self.logger.debug(f'Succesfully created meal plan {plan["id"]}: {title} with type {type}')

        return plan

    def get_meal_plans(self, date: datetime, **kwargs) -> Dict[str, Any]:
        url = f"{self.url}meal-plan/?from_date={date.strftime('%Y-%m-%d')}"
        return self.get_unpaged_results(url, "", **kwargs)

    def delete_meal_plan(self, obj_id: Union[str, int], **kwargs) -> None:
        url = f"{self.url}meal-plan/"
        self.delete_object(url, obj_id)
        self.logger.debug(f"Succesfully deleted meal plan {obj_id}.")

    @cached
    def get_food_substitutes(self, id: Union[str, int], substitute: str) -> List[Dict[str, Any]]:
        url = f"{self.url}{substitute}/{id}/substitutes/"
        self.logger.debug(f"Connecting to tandoor api at url: {url}")
        response = self.session.get(url, params={"onhand": 1}, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 200:
            self.logger.info(f"Failed to fetch food substitutes. Status code: {response.status_code}: {response.text}")
            raise TandoorAPIError(response.status_code, response.text)
        return json.loads(response.content)

    def get_meal_type(self, meal_type_id: Union[str, int], **kwargs) -> Dict[str, Any]:
        """Fetch a single meal type by ID."""
        url = f"{self.url}meal-type/"
        mt = self.get_unpaged_results(url, meal_type_id, **kwargs)
        self.logger.debug(f'Returning meal type {mt["id"]}: {mt["name"]}.')
        return mt

    def get_meal_types(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch all meal types from the API."""
        url = f"{self.url}meal-type/"
        self.logger.debug(f"Fetching meal types from: {url}")
        response = self.session.get(url, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 200:
            self.logger.info(f"Failed to fetch meal types. Status code: {response.status_code}: {response.text}")
            raise TandoorAPIError(response.status_code, response.text)
        return json.loads(response.content)

    def create_meal_type(self, name: str, color: str = "#FF5722", order: int = 0, **kwargs) -> Dict[str, Any]:
        """Create a new meal type."""
        url = f"{self.url}meal-type/"
        data = {"name": name, "color": color, "order": order}
        self.logger.debug(f"Creating meal type: {name} with color {color}")
        return self.create_object(url, data)

    def get_or_create_meal_type(self, name: str, color: str = "#FF5722", **kwargs) -> Dict[str, Any]:
        """Get existing meal type by name or create it with auto-incremented order."""
        meal_types = self.get_meal_types()
        for mt in meal_types:
            if mt["name"].lower() == name.lower():
                self.logger.debug(f"Found existing meal type: {mt['id']} - {mt['name']}")
                return mt
        # Auto-increment order based on existing max
        max_order = max((mt.get("order", 0) for mt in meal_types), default=-1)
        return self.create_meal_type(name, color, order=max_order + 1)

    def get_meal_plans_by_type(self, meal_type_id: int, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, **kwargs) -> List[Dict[str, Any]]:
        """Fetch meal plans filtered by meal type."""
        if from_date is None:
            from_date = now()
        if to_date is None:
            to_date = from_date

        url = f"{self.url}meal-plan/"
        params = {
            "meal_type": meal_type_id,
            "from_date": from_date.strftime("%Y-%m-%d"),
            "to_date": to_date.strftime("%Y-%m-%d"),
        }
        self.logger.debug(f"Fetching meal plans with type {meal_type_id}")
        response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 200:
            self.logger.info(f"Failed to fetch meal plans. Status code: {response.status_code}: {response.text}")
            raise TandoorAPIError(response.status_code, response.text)
        return json.loads(response.content)

    def cleanup_uncooked_meal_plans(self, meal_plan_type: int, days: int) -> int:
        """Delete meal plans older than `days` that have no matching cook log. Returns count deleted."""
        from datetime import timedelta

        to_date = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
        from_date = (now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Fetch meal plans in date range
        resp = self.session.get(
            f"{self.url}meal-plan/",
            params={"meal_type": meal_plan_type, "from_date": from_date, "to_date": to_date},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            self.logger.warning(f"Failed to fetch meal plans for cleanup: {resp.status_code}")
            return 0
        plans = resp.json()
        if isinstance(plans, dict):
            plans = plans.get("results", [])

        # Fetch cooked recipe IDs in the same range
        cook_resp = self.session.get(
            f"{self.url}cook-log/",
            params={"from_date": from_date, "to_date": to_date},
            timeout=DEFAULT_TIMEOUT,
        )
        cooked_ids: set = set()
        if cook_resp.status_code == 200:
            logs = cook_resp.json()
            if isinstance(logs, dict):
                logs = logs.get("results", [])
            cooked_ids = {log.get("recipe") for log in logs if log.get("recipe")}

        deleted = 0
        for plan in plans:
            recipe = plan.get("recipe")
            if recipe and recipe.get("id") not in cooked_ids:
                del_resp = self.session.delete(
                    f"{self.url}meal-plan/{plan['id']}/",
                    timeout=DEFAULT_TIMEOUT,
                )
                if del_resp.status_code in (200, 204):
                    deleted += 1
        self.logger.info(f"Cleanup: deleted {deleted} uncooked meal plans from {from_date} to {to_date}")
        return deleted

    def create_meal_plans_from_menu(
        self,
        meal_plan_type_id: int,
        recipes: List[Dict[str, Any]],
        date: Optional[str] = None,
        shared: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Create meal plan entries for a list of recipes.

        Returns {created, errors, total}.
        """
        # Fetch the full meal type object
        try:
            meal_type = self.get_meal_type(meal_plan_type_id)
        except (TandoorAPIError, TandoorNotFoundError) as e:
            self.logger.warning(f"Failed to fetch meal type {meal_plan_type_id}: {e}")
            return {"created": 0, "errors": [f"Invalid meal type {meal_plan_type_id}: {e}"], "total": len(recipes)}

        plan_date = date or now().strftime("%Y-%m-%d")
        shared_objs = [{"id": uid} for uid in (shared or [])]
        created = 0
        errors: List[str] = []
        for recipe in recipes:
            data = {
                "title": recipe["name"],
                "recipe": {"id": recipe["id"], "name": recipe["name"], "keywords": []},
                "servings": 1,
                "note": "",
                "shared": shared_objs,
                "from_date": plan_date,
                "to_date": plan_date,
                "meal_type": meal_type,
            }
            try:
                resp = self.session.post(f"{self.url}meal-plan/", json=data, timeout=DEFAULT_TIMEOUT)
                if resp.status_code in (200, 201):
                    created += 1
                else:
                    errors.append(f"{recipe['name']}: {resp.status_code} {resp.text[:100]}")
            except Exception as e:
                errors.append(f"{recipe['name']}: {e}")
        self.logger.info(f"Created {created}/{len(recipes)} meal plan entries")
        return {"created": created, "errors": errors, "total": len(recipes)}

    def create_order_meal_plan(
        self,
        recipe_id: int,
        recipe_name: str,
        meal_type: Dict[str, Any],
        servings: int = 1,
        note: Optional[str] = None,
        date: Optional[datetime] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a meal plan entry for an order."""
        if date is None:
            date = now()
        url = f"{self.url}meal-plan/"
        data = {
            "title": recipe_name,
            "recipe": {"id": recipe_id, "name": recipe_name, "keywords": []},
            "servings": servings,
            "note": note or f"Ordered at {now().strftime('%H:%M:%S')}",
            "from_date": date.strftime("%Y-%m-%d"),
            "to_date": date.strftime("%Y-%m-%d"),
            "meal_type": meal_type,
        }
        self.logger.debug(f"Creating order meal plan for recipe {recipe_id}")
        return self.create_object(url, data)
