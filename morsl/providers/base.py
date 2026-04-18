"""Abstract recipe provider interface.

Defines the contract that all recipe data sources must implement.
morsl's service layer programs against this interface — not against
any specific recipe app's API.

Terminology mapping:
    morsl generic  → Tandoor        → Mealie         → Paprika
    tag            → keyword        → tag            → category
    ingredient     → food           → food           → ingredient
    collection     → book           → cookbook        → (none)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Flag, auto
from typing import Any, Dict, List, Optional, Union


class Capability(Flag):
    """Optional features a provider may support.

    Services check ``provider.capabilities()`` before calling optional
    methods. Features degrade gracefully when a capability is absent.
    """

    ONHAND = auto()
    SHOPPING_LIST = auto()
    MEAL_PLAN = auto()
    NUTRITION = auto()
    SEARCH = auto()
    SUBSTITUTES = auto()


class RecipeProvider(ABC):
    """Abstract interface for recipe data sources.

    Core methods are required — every provider must implement them.
    Optional methods have default implementations that return empty
    results or raise NotImplementedError; providers declare support
    via ``capabilities()``.
    """

    @abstractmethod
    def capabilities(self) -> Capability:
        """Declare which optional features this provider supports."""
        ...

    # -- Core: recipe queries --------------------------------------------------

    @abstractmethod
    def get_recipes(
        self,
        params: Optional[Dict[str, Any]] = None,
        filters: Union[List[int], int, None] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Fetch a list of recipes, optionally filtered."""
        ...

    @abstractmethod
    def get_recipe_details(self, recipe_id: Union[str, int]) -> Dict[str, Any]:
        """Fetch full details for a single recipe."""
        ...

    # -- Core: tag queries (Tandoor: keywords) ---------------------------------

    @abstractmethod
    def get_tag_tree(self, tag_id: Union[str, int], **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch a tag and all its descendants."""
        ...

    @abstractmethod
    def get_tag(self, tag_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        """Fetch a single tag by ID."""
        ...

    # -- Core: ingredient queries (Tandoor: foods) -----------------------------

    @abstractmethod
    def get_ingredient(self, ingredient_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        """Fetch a single ingredient by ID."""
        ...

    # -- Core: collection queries (Tandoor: books) -----------------------------

    @abstractmethod
    def get_collection(self, collection_id: Union[str, int], **kwargs: Any) -> Dict[str, Any]:
        """Fetch a single recipe collection by ID."""
        ...

    @abstractmethod
    def get_collection_recipes(self, collection: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch all recipes in a collection."""
        ...

    # -- Optional: declared via capabilities() ---------------------------------

    def get_mealplan_recipes(
        self,
        mealtype_id: Optional[Union[List[int], int]] = None,
        date: Any = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Fetch recipes from a meal plan (requires MEAL_PLAN capability)."""
        return []

    def get_ingredient_substitutes(
        self, ingredient_id: Union[str, int], substitute_type: str
    ) -> List[Dict[str, Any]]:
        """Find on-hand substitutes for an ingredient (requires SUBSTITUTES)."""
        return []

    def get_onhand_items(self) -> List[Dict[str, Any]]:
        """Fetch ingredients currently on hand (requires ONHAND capability)."""
        return []

    def get_custom_filters(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch saved custom filters from the provider."""
        return []
