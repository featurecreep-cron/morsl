from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_credentials, get_settings_service, require_admin
from app.api.models import MealTypeCreateRequest, RatingRequest
from constants import DEFAULT_TIMEOUT
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proxy"])


def _proxy_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Forward a GET request to the Tandoor API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error: {response.text}",
        )
    return response.json()


@router.get("/recipe/{recipe_id}")
def get_recipe(
    recipe_id: int,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy to Tandoor recipe details."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/recipe/{recipe_id}"
    return _proxy_get(api_url, token)


@router.get("/foods", dependencies=[Depends(require_admin)])
def search_foods(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy food search to Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/food/"
    return _proxy_get(api_url, token, params={"query": search, "page_size": 50})


@router.get("/foods/{food_id}", dependencies=[Depends(require_admin)])
def get_food(
    food_id: int,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy to Tandoor food details by ID."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/food/{food_id}/"
    return _proxy_get(api_url, token)


@router.get("/keywords", dependencies=[Depends(require_admin)])
def list_keywords(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy keyword listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/keyword/"
    params: Dict[str, Any] = {"page_size": 200}
    if search:
        params["query"] = search
    return _proxy_get(api_url, token, params=params)


@router.get("/books", dependencies=[Depends(require_admin)])
def search_books(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy recipe book search to Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/recipe-book/"
    params: Dict[str, Any] = {"page_size": 50}
    if search:
        params["query"] = search
    return _proxy_get(api_url, token, params=params)


@router.get("/meal-types")
def list_meal_types(
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy meal type listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/meal-type/"
    return _proxy_get(api_url, token)


@router.post("/meal-types", dependencies=[Depends(require_admin)])
def create_meal_type(
    body: MealTypeCreateRequest,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Create a new meal type in Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/meal-type/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = requests.post(api_url, headers=headers, json={"name": body.name, "color": body.color or "#FF5722"}, timeout=DEFAULT_TIMEOUT)
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error: {response.text}",
        )
    return response.json()


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy user listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/user/"
    return _proxy_get(api_url, token)


@router.patch("/recipe/{recipe_id}/rating")
def set_rating(
    recipe_id: int,
    body: RatingRequest,
    credentials: tuple[str, str] = Depends(get_credentials),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> Any:
    """Update a recipe's rating in Tandoor and create a cook log entry."""
    app_settings = settings_svc.get_all()
    if not app_settings.get("ratings_enabled", True):
        raise HTTPException(status_code=403, detail="Ratings are currently disabled")
    if not app_settings.get("save_ratings_to_tandoor", True):
        return {"status": "ok", "rating": body.rating}

    url, token = credentials
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Update the recipe's rating
    api_url = f"{url.rstrip('/')}/api/recipe/{recipe_id}/"
    response = requests.patch(api_url, headers=headers, json={"rating": body.rating}, timeout=DEFAULT_TIMEOUT)
    if response.status_code not in (200, 204):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error: {response.text}",
        )

    # Create a cook log entry to record who rated
    comment = f"Rated by {body.customer_name}" if body.customer_name else None
    cook_log_url = f"{url.rstrip('/')}/api/cook-log/"
    cook_log_data = {
        "recipe": recipe_id,
        "rating": int(body.rating),
        "comment": comment,
    }
    try:
        requests.post(cook_log_url, headers=headers, json=cook_log_data, timeout=DEFAULT_TIMEOUT)
    except Exception as e:
        logger.warning(f"Failed to create cook log for recipe {recipe_id}: {e}")

    if response.content:
        return response.json()
    return {"status": "ok"}
