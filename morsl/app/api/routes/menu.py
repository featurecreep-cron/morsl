from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import get_generation_service, require_admin
from morsl.app.api.models import GenerationStatusResponse, MenuResponse
from morsl.services.generation_service import GenerationService

router = APIRouter(tags=["menu"])


@router.get("/menu", response_model=MenuResponse)
def get_menu(
    gen_service: GenerationService = Depends(get_generation_service),
) -> MenuResponse:
    """Get the current generated menu."""
    menu_data = gen_service.get_current_menu()
    if menu_data is None:
        raise HTTPException(status_code=404, detail="No menu has been generated yet")
    return MenuResponse(**menu_data)


@router.delete("/menu", status_code=204, dependencies=[Depends(require_admin)])
def delete_menu(
    gen_service: GenerationService = Depends(get_generation_service),
) -> None:
    """Clear the current menu data."""
    gen_service.clear_menu()


@router.get("/status", response_model=GenerationStatusResponse)
def get_status(
    gen_service: GenerationService = Depends(get_generation_service),
) -> GenerationStatusResponse:
    """Get the current generation status."""
    status = gen_service.get_status()
    return GenerationStatusResponse(
        state=status.state.value,
        request_id=status.request_id,
        started_at=status.started_at,
        completed_at=status.completed_at,
        error=status.error,
        recipe_count=status.recipe_count,
        warnings=status.warnings,
    )
