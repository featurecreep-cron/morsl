from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from morsl.app.api.dependencies import get_credentials, get_settings_service, require_admin
from morsl.app.api.models import MealTypeCreateRequest, RatingRequest
from morsl.constants import HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT
from morsl.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proxy"])

_TIMEOUT = httpx.Timeout(
    connect=HTTP_CONNECT_TIMEOUT,
    read=HTTP_READ_TIMEOUT,
    write=HTTP_READ_TIMEOUT,
    pool=HTTP_READ_TIMEOUT,
)

# Module-level shared client — created lazily on first use
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


def _headers(token: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


async def _proxy_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Forward a GET request to the Tandoor API."""
    client = _get_client()
    response = await client.get(url, headers=_headers(token), params=params)
    if response.status_code != 200:
        logger.warning("Tandoor API error %d for %s: %s", response.status_code, url, response.text)
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error (HTTP {response.status_code})",
        )
    return response.json()


@router.get("/recipe/{recipe_id}")
async def get_recipe(
    recipe_id: int,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy to Tandoor recipe details."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/recipe/{recipe_id}"
    return await _proxy_get(api_url, token)


@router.get("/foods", dependencies=[Depends(require_admin)])
async def search_foods(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy food search to Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/food/"
    return await _proxy_get(api_url, token, params={"query": search, "page_size": 50})


@router.get("/foods/{food_id}", dependencies=[Depends(require_admin)])
async def get_food(
    food_id: int,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy to Tandoor food details by ID."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/food/{food_id}/"
    return await _proxy_get(api_url, token)


@router.get("/keywords", dependencies=[Depends(require_admin)])
async def list_keywords(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy keyword listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/keyword/"
    params: Dict[str, Any] = {"page_size": 200}
    if search:
        params["query"] = search
    return await _proxy_get(api_url, token, params=params)


@router.get("/books", dependencies=[Depends(require_admin)])
async def search_books(
    search: str = Query(default=""),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy recipe book search to Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/recipe-book/"
    params: Dict[str, Any] = {"page_size": 50}
    if search:
        params["query"] = search
    return await _proxy_get(api_url, token, params=params)


@router.get("/custom-filters", dependencies=[Depends(require_admin)])
async def list_custom_filters(
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy custom filter listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/custom-filter/"
    return await _proxy_get(api_url, token, params={"page_size": 100})


@router.get("/meal-types")
async def list_meal_types(
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy meal type listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/meal-type/"
    return await _proxy_get(api_url, token)


@router.post("/meal-types", dependencies=[Depends(require_admin)])
async def create_meal_type(
    body: MealTypeCreateRequest,
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Create a new meal type in Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/meal-type/"
    client = _get_client()
    response = await client.post(
        api_url,
        headers=_headers(token),
        json={"name": body.name, "color": body.color or "#FF5722"},
    )
    if response.status_code not in (200, 201):
        logger.warning(
            "Tandoor API error %d creating meal type: %s", response.status_code, response.text
        )
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error (HTTP {response.status_code})",
        )
    return response.json()


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users(
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Any:
    """Proxy user listing from Tandoor."""
    url, token = credentials
    api_url = f"{url.rstrip('/')}/api/user/"
    return await _proxy_get(api_url, token)


@router.patch("/recipe/{recipe_id}/rating")
async def set_rating(
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
    hdrs = _headers(token)
    client = _get_client()

    # Update the recipe's rating
    api_url = f"{url.rstrip('/')}/api/recipe/{recipe_id}/"
    response = await client.patch(api_url, headers=hdrs, json={"rating": body.rating})
    if response.status_code not in (200, 204):
        logger.warning(
            "Tandoor API error %d for rating recipe %d: %s",
            response.status_code,
            recipe_id,
            response.text,
        )
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tandoor API error (HTTP {response.status_code})",
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
        await client.post(cook_log_url, headers=hdrs, json=cook_log_data)
    except httpx.HTTPError as e:
        logger.warning(f"Failed to create cook log for recipe {recipe_id}: {e}")

    if response.content:
        return response.json()
    return {"status": "ok"}
