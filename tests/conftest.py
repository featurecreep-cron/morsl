from __future__ import annotations

from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from models import Recipe


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.loglevel = 20  # INFO
    return logger


def make_recipe(
    id: int,
    name: str = "Test Recipe",
    keywords: Optional[List[Dict]] = None,
    rating: float = 0,
    last_cooked: Optional[str] = None,
    created_at: str = "2024-01-15T12:00:00+00:00",
    servings: int = 4,
) -> Recipe:
    """Factory to create Recipe objects with configurable fields."""
    if keywords is None:
        keywords = []
    return Recipe({
        "id": id,
        "name": name,
        "description": f"Description for {name}",
        "new": False,
        "servings": servings,
        "keywords": keywords,
        "rating": rating,
        "last_cooked": last_cooked,
        "created_at": created_at,
    })


@pytest.fixture
def recipe_factory():
    return make_recipe


@pytest.fixture
def sample_recipes():
    """10 diverse recipes for constraint testing."""
    return [
        make_recipe(1, "Pasta Carbonara", keywords=[{"id": 10, "name": "Italian"}, {"id": 20, "name": "Pasta"}], rating=4.5, last_cooked="2024-06-01T12:00:00+00:00", created_at="2023-01-10T12:00:00+00:00"),
        make_recipe(2, "Tacos", keywords=[{"id": 30, "name": "Mexican"}], rating=3.0, last_cooked="2024-05-15T12:00:00+00:00", created_at="2023-02-20T12:00:00+00:00"),
        make_recipe(3, "Sushi", keywords=[{"id": 40, "name": "Japanese"}], rating=5.0, last_cooked=None, created_at="2023-03-05T12:00:00+00:00"),
        make_recipe(4, "Pizza", keywords=[{"id": 10, "name": "Italian"}], rating=4.0, last_cooked="2024-07-01T12:00:00+00:00", created_at="2023-04-15T12:00:00+00:00"),
        make_recipe(5, "Burger", keywords=[{"id": 50, "name": "American"}], rating=3.5, last_cooked="2024-03-01T12:00:00+00:00", created_at="2023-05-25T12:00:00+00:00"),
        make_recipe(6, "Pad Thai", keywords=[{"id": 60, "name": "Thai"}], rating=4.0, last_cooked="2024-04-01T12:00:00+00:00", created_at="2023-06-10T12:00:00+00:00"),
        make_recipe(7, "Ramen", keywords=[{"id": 40, "name": "Japanese"}], rating=4.5, last_cooked="2024-08-01T12:00:00+00:00", created_at="2023-07-20T12:00:00+00:00"),
        make_recipe(8, "Lasagna", keywords=[{"id": 10, "name": "Italian"}, {"id": 20, "name": "Pasta"}], rating=3.0, last_cooked="2024-01-01T12:00:00+00:00", created_at="2023-08-15T12:00:00+00:00"),
        make_recipe(9, "Fish and Chips", keywords=[{"id": 70, "name": "British"}], rating=2.5, last_cooked=None, created_at="2023-09-01T12:00:00+00:00"),
        make_recipe(10, "Curry", keywords=[{"id": 80, "name": "Indian"}], rating=4.0, last_cooked="2024-09-01T12:00:00+00:00", created_at="2023-10-10T12:00:00+00:00"),
    ]


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.url = "http://localhost/api/"
    api.progress = None
    return api
