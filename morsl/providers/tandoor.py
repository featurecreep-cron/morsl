"""Tandoor recipe provider — wraps TandoorAPI behind the RecipeProvider interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from morsl.providers.base import Capability, RecipeProvider
from morsl.tandoor_api import TandoorAPI


class TandoorProvider(RecipeProvider):
    """RecipeProvider backed by a Tandoor Recipes instance.

    Wraps the existing ``TandoorAPI`` HTTP client, mapping Tandoor's
    vocabulary (keywords, foods, books) to morsl's generic terms
    (tags, ingredients, collections).

    The underlying ``TandoorAPI`` is accessible via the ``.api`` property
    for operations that are Tandoor-specific and not part of the generic
    provider interface (e.g. meal plan CRUD, meal type management).
    """

    def __init__(self, api: TandoorAPI) -> None:
        self._api = api

    @property
    def api(self) -> TandoorAPI:
        """Direct access to the Tandoor HTTP client.

        Use this for Tandoor-specific operations that don't belong on
        the generic provider interface (meal plans, orders, etc.).
        """
        return self._api

    def capabilities(self) -> Capability:
        return (
            Capability.ONHAND | Capability.MEAL_PLAN | Capability.SUBSTITUTES | Capability.SEARCH
        )

    # -- Core: recipe queries --------------------------------------------------

    def get_recipes(
        self,
        params: Optional[Dict[str, Any]] = None,
        filters: Union[List[int], int, None] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._api.get_recipes(params=params, filters=filters, **kwargs)

    def get_recipe_details(self, recipe_id: Union[str, int]) -> Dict[str, Any]:
        return self._api.get_recipe_details(recipe_id)

    # -- Core: tag queries (Tandoor keywords) ----------------------------------

    def get_tag_tree(self, tag_id: Union[str, int], **kwargs: Any) -> List[Dict[str, Any]]:
        return self._api.get_keyword_tree(tag_id, **kwargs)

    def get_tag(self, tag_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        return self._api.get_keyword(tag_id, **kwargs)

    # -- Core: ingredient queries (Tandoor foods) ------------------------------

    def get_ingredient(self, ingredient_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        return self._api.get_food(ingredient_id, **kwargs)

    # -- Core: collection queries (Tandoor books) ------------------------------

    def get_collection(self, collection_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        return self._api.get_book(collection_id, **kwargs)

    def get_collection_recipes(self, collection: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return self._api.get_book_recipes(collection, **kwargs)

    # -- Optional capabilities -------------------------------------------------

    def get_mealplan_recipes(
        self,
        mealtype_id: Optional[Union[List[int], int]] = None,
        date: Any = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._api.get_mealplan_recipes(mealtype_id=mealtype_id, date=date, **kwargs)

    def get_ingredient_substitutes(
        self, ingredient_id: Union[str, int], substitute_type: str
    ) -> List[Dict[str, Any]]:
        return self._api.get_food_substitutes(ingredient_id, substitute_type)

    def get_onhand_items(self) -> List[Dict[str, Any]]:
        return self._api.get_onhand_foods()

    def get_custom_filters(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return self._api.get_custom_filters(**kwargs)
