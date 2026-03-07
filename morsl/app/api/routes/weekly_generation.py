from __future__ import annotations

from datetime import date
from logging import Logger

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import (
    get_config_service,
    get_credentials,
    get_generation_service,
    get_logger,
    get_meal_plan_service,
    get_settings_service,
    get_template_service,
    get_weekly_generation_service,
    require_admin,
)
from morsl.app.api.models import (
    GenerateResponse,
    WeeklyGenerateRequest,
    WeeklyGenerationStatusResponse,
    WeeklyRegenerateSlotRequest,
    WeeklySaveRequest,
    WeeklySaveResponse,
)
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationService, GenerationState
from morsl.services.meal_plan_service import MealPlanService
from morsl.services.settings_service import SettingsService
from morsl.services.template_service import TemplateService
from morsl.services.weekly_generation_service import WeeklyGenerationService

router = APIRouter(prefix="/weekly", tags=["weekly"], dependencies=[Depends(require_admin)])


@router.post("/generate/{template}", status_code=202, response_model=GenerateResponse)
async def generate_weekly(
    template: str,
    request: WeeklyGenerateRequest,
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
    template_svc: TemplateService = Depends(get_template_service),
    config_svc: ConfigService = Depends(get_config_service),
    gen_svc: GenerationService = Depends(get_generation_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> GenerateResponse:
    """Start weekly plan generation for a template."""
    # Verify template exists and is valid
    try:
        tpl = template_svc.get_template(template)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    errors = template_svc.validate_template(tpl, config_svc)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    # Check single-menu generation isn't running
    if gen_svc.get_status().state == GenerationState.GENERATING:
        raise HTTPException(status_code=409, detail="A single-menu generation is in progress")

    week_start = None
    if request.week_start:
        try:
            week_start = date.fromisoformat(request.week_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid week_start date format (use YYYY-MM-DD)") from None

    url, token = credentials
    try:
        request_id = await weekly_svc.start_generation(
            template_name=template,
            template_service=template_svc,
            config_service=config_svc,
            url=url,
            token=token,
            app_logger=logger,
            week_start=week_start,
            generation_service=gen_svc,
            settings_service=settings_svc,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None

    return GenerateResponse(request_id=request_id, status="generating")


@router.get("/status", response_model=WeeklyGenerationStatusResponse)
def get_weekly_status(
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
) -> WeeklyGenerationStatusResponse:
    """Get current weekly generation status."""
    s = weekly_svc.get_status()
    return WeeklyGenerationStatusResponse(
        state=s.state.value,
        request_id=s.request_id,
        started_at=s.started_at,
        completed_at=s.completed_at,
        error=s.error,
        template=s.template,
        profile_progress=s.profile_progress,
        warnings=s.warnings,
    )


@router.get("/plan/{template}")
def get_weekly_plan(
    template: str,
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
) -> dict:
    """Get a generated weekly plan."""
    try:
        plan = weekly_svc.get_plan(template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if not plan:
        raise HTTPException(status_code=404, detail=f"No plan found for template '{template}'")
    return plan


@router.delete("/plan/{template}", status_code=204)
def delete_weekly_plan(
    template: str,
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
) -> None:
    """Delete a generated weekly plan."""
    try:
        removed = weekly_svc.clear_plan(template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if not removed:
        raise HTTPException(status_code=404, detail=f"No plan found for template '{template}'")


@router.post("/regenerate-slot", response_model=GenerateResponse)
async def regenerate_slot(
    request: WeeklyRegenerateSlotRequest,
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
    template_svc: TemplateService = Depends(get_template_service),
    config_svc: ConfigService = Depends(get_config_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> GenerateResponse:
    """Regenerate a single slot in a weekly plan (synchronous)."""
    if weekly_svc.get_status().state == GenerationState.GENERATING:
        raise HTTPException(status_code=409, detail="A weekly generation is in progress")

    url, token = credentials
    try:
        await weekly_svc.regenerate_slot(
            template_name=request.template,
            target_date=request.date,
            meal_type_id=request.meal_type_id,
            template_service=template_svc,
            config_service=config_svc,
            url=url,
            token=token,
            app_logger=logger,
            settings_service=settings_svc,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return GenerateResponse(request_id="", status="complete")


@router.post("/save", response_model=WeeklySaveResponse)
def save_weekly_plan(
    request: WeeklySaveRequest,
    weekly_svc: WeeklyGenerationService = Depends(get_weekly_generation_service),
    meal_plan_svc: MealPlanService = Depends(get_meal_plan_service),
) -> WeeklySaveResponse:
    """Save a weekly plan to Tandoor as meal plans."""
    try:
        plan = weekly_svc.get_plan(request.template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if not plan:
        raise HTTPException(status_code=404, detail=f"No plan found for template '{request.template}'")

    result = meal_plan_svc.save_weekly_plan(plan, shared=request.shared)
    return WeeklySaveResponse(**result)
