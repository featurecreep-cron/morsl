from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from tandoor_api import TandoorAPI


class TandoorEntity:
    id: int
    name: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TandoorEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.id}: <{self.name}>"

    def __str__(self) -> str:
        return self.name


class Food(TandoorEntity):
    def __init__(self, data: dict) -> None:
        self.id = data.get("id", None)
        self.name = data.get("name", None)
        self.recipe = data.get("recipe", None)
        self.shopping = data.get("shopping", None)
        self.onhand = data.get("food_onhand", None)
        self.ignore_shopping = data.get("ignore_shopping", None)
        self.substitute_onhand = data.get("substitute_onhand", None)


class Unit(TandoorEntity):
    def __init__(self, data: dict) -> None:
        self.id = data.get("id", None)
        self.name = data.get("name", None)


class Recipe(TandoorEntity):
    def __init__(self, data: dict, get_food: bool = False) -> None:
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.new = data["new"]
        self.servings = data["servings"]
        self.keywords = [kw["id"] for kw in data["keywords"]]
        self.keyword_names = {kw["id"]: kw.get("name", "") for kw in data["keywords"]}
        try:
            self.cookedon = datetime.fromisoformat(data["last_cooked"])
        except (ValueError, TypeError):
            self.cookedon = None
        self.createdon = datetime.fromisoformat(data["created_at"])
        self.rating = data["rating"]
        self.ingredients = []

    @staticmethod
    def recipesWithKeyword(recipes: List["Recipe"], keywords: List["Keyword"]) -> List["Recipe"]:
        """Return recipes containing any of the given keywords."""
        return [r for r in recipes if any(k in r.keywords for k in [x.id for x in keywords])]

    @staticmethod
    def recipesWithDate(recipes: List["Recipe"], field: str, date: datetime, after: bool = True) -> List["Recipe"]:
        """Return recipes where *field* (createdon/cookedon) is before/after *date*."""
        if after:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d > date]

        else:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d < date]

    @staticmethod
    def recipesWithRating(recipes: List["Recipe"], rating: int) -> List["Recipe"]:
        """Return recipes matching *rating*. Negative means <= abs(rating)."""
        lessthan = rating < 0
        if lessthan:
            return [r for r in recipes if 0 < (getattr(r, "rating", None) or 0) <= abs(rating)]
        else:
            return [r for r in recipes if getattr(r, "rating", 0) >= rating]

    def addDetails(self, api: "TandoorAPI") -> None:
        """Populate self.ingredients, substituting on-hand foods where possible."""
        recipe = api.get_recipe_details(self.id)
        for f in [i["food"] for s in recipe["steps"] for i in s["ingredients"]]:
            if f is None:
                continue
            if not f["food_onhand"]:
                onhand_substitutes = api.get_food_substitutes(f["id"], substitute="food")
                if onhand_substitutes:
                    f = api.get_food(random.choice(onhand_substitutes)["id"])
            self.ingredients.append(Food(f))


class Keyword(TandoorEntity):
    def __init__(self, data: dict) -> None:
        self.id = data["id"]
        self.name = data["name"]


class Book(TandoorEntity):
    def __init__(self, data: dict) -> None:
        self.id = data["id"]
        self.name = data["name"]
        if f := data.get("filter", None):
            self.filter = f.get("id", None)
        else:
            self.filter = None


@dataclass
class RelaxedConstraint:
    label: str
    slack_value: float
    weight: float


@dataclass
class SolverResult:
    recipes: List[Recipe]
    requested_count: int
    constraint_count: int
    relaxed_constraints: List[RelaxedConstraint] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "optimal"
