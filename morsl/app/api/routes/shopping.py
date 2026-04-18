from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import PlainTextResponse

from morsl.app.api.dependencies import get_generation_service, get_provider
from morsl.app.api.models import ShoppingListResponse
from morsl.services.generation_service import GenerationService
from morsl.services.shopping_service import generate_shopping_list, get_onhand_names

router = APIRouter(tags=["shopping"])


def _get_menu_recipes(gen_service: GenerationService):
    """Get recipes from current menu or raise 404."""
    menu = gen_service.get_current_menu()
    if menu is None:
        raise HTTPException(status_code=404, detail="No menu has been generated yet")
    return menu.get("recipes", [])


@router.post("/shopping-list", response_model=ShoppingListResponse)
def create_shopping_list(
    exclude_onhand: bool = Query(False, description="Exclude on-hand ingredients"),
    gen_service: GenerationService = Depends(get_generation_service),
    provider=Depends(get_provider),
) -> ShoppingListResponse:
    """Generate a shopping list from the current menu."""
    recipes = _get_menu_recipes(gen_service)
    onhand = get_onhand_names(provider) if exclude_onhand else None
    shopping_list = generate_shopping_list(recipes, exclude_onhand=onhand)
    return ShoppingListResponse(**shopping_list.to_dict())


@router.post("/shopping-list/text")
def create_shopping_list_text(
    exclude_onhand: bool = Query(False, description="Exclude on-hand ingredients"),
    gen_service: GenerationService = Depends(get_generation_service),
    provider=Depends(get_provider),
) -> PlainTextResponse:
    """Generate a plain-text shopping list for clipboard copy."""
    recipes = _get_menu_recipes(gen_service)
    onhand = get_onhand_names(provider) if exclude_onhand else None
    shopping_list = generate_shopping_list(recipes, exclude_onhand=onhand)
    return PlainTextResponse(shopping_list.to_text())
