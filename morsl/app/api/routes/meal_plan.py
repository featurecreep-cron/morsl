from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from morsl.app.api.dependencies import (
    get_generation_service,
    get_meal_plan_service,
    get_settings_service,
    require_admin,
)
from morsl.app.api.models import MealPlanSaveRequest
from morsl.services.generation_service import GenerationService
from morsl.services.meal_plan_service import MealPlanService
from morsl.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["meal-plan"])


@router.post("/meal-plan", dependencies=[Depends(require_admin)])
def save_meal_plan(
    body: MealPlanSaveRequest,
    gen_svc: GenerationService = Depends(get_generation_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    meal_plan_svc: MealPlanService = Depends(get_meal_plan_service),
) -> Any:
    """Push the current menu to Tandoor as meal plan entries."""
    app_settings = settings_svc.get_all()
    if not app_settings.get("meal_plan_enabled", False):
        raise HTTPException(status_code=403, detail="Meal plan saving is disabled")

    if body.recipes is not None:
        recipes = [{"id": r.id, "name": r.name} for r in body.recipes]
    else:
        menu = gen_svc.get_current_menu()
        if not menu or not menu.get("recipes"):
            raise HTTPException(status_code=404, detail="No current menu to save")
        recipes = menu["recipes"]

    if not recipes:
        raise HTTPException(status_code=404, detail="No recipes to save")

    result = meal_plan_svc.save_menu(
        meal_plan_type_id=body.meal_type_id,
        recipes=recipes,
        date=body.date,
        shared=body.shared,
    )

    # Return 207 Multi-Status when some (but not all) succeeded, 400 when none did
    if result["errors"]:
        status = 400 if result["created"] == 0 else 207
        return JSONResponse(content=result, status_code=status)

    return result
