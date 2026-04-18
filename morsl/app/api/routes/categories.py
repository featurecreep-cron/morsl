from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import get_category_service, get_config_service, require_admin
from morsl.app.api.models import CategoryRequest, CategoryResponse
from morsl.services.category_service import CategoryService
from morsl.services.config_service import ConfigService

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(
    svc: CategoryService = Depends(get_category_service),
) -> List[CategoryResponse]:
    """List all categories."""
    return [CategoryResponse(**c) for c in svc.list_categories()]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_category(
    body: CategoryRequest,
    svc: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Create a new category."""
    try:
        category = svc.create_category(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return CategoryResponse(**category)


@router.put(
    "/categories/reorder",
    response_model=List[CategoryResponse],
    dependencies=[Depends(require_admin)],
)
def reorder_categories(
    body: List[str],
    svc: CategoryService = Depends(get_category_service),
) -> List[CategoryResponse]:
    """Reorder categories by providing an ordered list of IDs."""
    return [CategoryResponse(**c) for c in svc.reorder_categories(body)]


@router.put(
    "/categories/{cat_id}", response_model=CategoryResponse, dependencies=[Depends(require_admin)]
)
def update_category(
    cat_id: str,
    body: CategoryRequest,
    svc: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Update an existing category."""
    try:
        category = svc.update_category(cat_id, body.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Category not found: {cat_id}") from None
    return CategoryResponse(**category)


@router.delete("/categories/{cat_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_category(
    cat_id: str,
    svc: CategoryService = Depends(get_category_service),
    config_svc: ConfigService = Depends(get_config_service),
) -> None:
    """Delete a category and clear it from affected profiles."""
    try:
        svc.delete_category(cat_id, config_service=config_svc)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Category not found: {cat_id}") from None
