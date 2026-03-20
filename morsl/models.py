from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# eq=False on all subclasses prevents dataclass-generated __eq__ from
# shadowing the id-based equality defined here.
@dataclass(frozen=True, eq=False)
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


@dataclass(frozen=True, eq=False)
class Food(TandoorEntity):
    recipe: Optional[int] = None
    shopping: Optional[bool] = None
    onhand: Optional[bool] = None
    ignore_shopping: Optional[bool] = None
    substitute_onhand: Optional[bool] = None


# Unit and Keyword are structurally identical but semantically distinct —
# the solver and constraint system need to distinguish them by type.
@dataclass(frozen=True, eq=False)
class Unit(TandoorEntity):
    pass


@dataclass(frozen=True, eq=False)
class Keyword(TandoorEntity):
    pass


@dataclass(frozen=True, eq=False)
class Book(TandoorEntity):
    filter: Optional[int] = None


@dataclass(frozen=True, eq=False)
class Recipe(TandoorEntity):
    description: str = ""
    new: bool = False
    servings: int = 1
    keywords: tuple[int, ...] = ()
    # Frozen dataclasses can't use field(default_factory=dict), so we use
    # None + __post_init__ to avoid sharing a mutable default across instances.
    keyword_names: dict[int, str] = None  # type: ignore[assignment]
    cookedon: Optional[datetime] = None
    createdon: Optional[datetime] = None
    rating: float = 0

    def __post_init__(self) -> None:
        if self.keyword_names is None:
            object.__setattr__(self, "keyword_names", {})

    @staticmethod
    def recipes_with_keyword(recipes: list[Recipe], keywords: list[Keyword]) -> list[Recipe]:
        """Return recipes containing any of the given keywords."""
        kw_ids = {k.id for k in keywords}
        return [r for r in recipes if kw_ids.intersection(r.keywords)]

    @staticmethod
    def recipes_with_date(
        recipes: list[Recipe], field: str, date: datetime, after: bool = True
    ) -> list[Recipe]:
        """Return recipes where *field* (createdon/cookedon) is before/after *date*."""
        if after:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d > date]
        else:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d < date]

    @staticmethod
    def recipes_with_rating(recipes: list[Recipe], rating: int) -> list[Recipe]:
        """Return recipes matching *rating*. Negative means <= abs(rating)."""
        if rating < 0:
            return [r for r in recipes if 0 < (r.rating or 0) <= abs(rating)]
        return [r for r in recipes if (r.rating or 0) >= rating]


@dataclass(frozen=True)
class RelaxedConstraint:
    label: str
    slack_value: float
    weight: float


@dataclass(frozen=True)
class SolverResult:
    recipes: tuple[Recipe, ...] = ()
    requested_count: int = 0
    constraint_count: int = 0
    relaxed_constraints: tuple[RelaxedConstraint, ...] = ()
    warnings: tuple[str, ...] = ()
    status: str = "optimal"


# -- Factory functions for constructing from Tandoor API dicts --


def make_food(data: dict) -> Food:
    """Create a Food from a Tandoor API response dict."""
    return Food(
        id=data["id"],
        name=data["name"],
        recipe=data.get("recipe"),
        shopping=data.get("shopping"),
        onhand=data.get("food_onhand"),
        ignore_shopping=data.get("ignore_shopping"),
        substitute_onhand=data.get("substitute_onhand"),
    )


def make_keyword(data: dict) -> Keyword:
    """Create a Keyword from a Tandoor API response dict."""
    return Keyword(id=data["id"], name=data["name"])


def make_book(data: dict) -> Book:
    """Create a Book from a Tandoor API response dict."""
    f = data.get("filter")
    return Book(id=data["id"], name=data["name"], filter=f.get("id") if f else None)


def make_recipe(data: dict) -> Recipe:
    """Create a Recipe from a Tandoor API response dict."""
    try:
        cookedon = datetime.fromisoformat(data["last_cooked"]) if data.get("last_cooked") else None
    except (ValueError, TypeError):
        cookedon = None
    return Recipe(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        new=data.get("new", False),
        servings=data.get("servings", 1),
        keywords=tuple(kw["id"] for kw in data.get("keywords", [])),
        keyword_names={kw["id"]: kw.get("name", "") for kw in data.get("keywords", [])},
        cookedon=cookedon,
        createdon=datetime.fromisoformat(data["created_at"]),
        rating=data.get("rating", 0) or 0,  # API returns null for unrated
    )
