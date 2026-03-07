from __future__ import annotations

from logging import Logger

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import get_config_service, get_credentials, get_generation_service, get_logger, get_settings_service, require_admin
from morsl.app.api.models import GenerateRequest, GenerateResponse
from morsl.constants import API_CACHE_TTL_MINUTES
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationService, GenerationState
from morsl.services.settings_service import SettingsService

router = APIRouter(tags=["generation"], dependencies=[Depends(require_admin)])


@router.post("/generate", status_code=202, response_model=GenerateResponse)
async def generate_default(
    gen_service: GenerationService = Depends(get_generation_service),
    config_service: ConfigService = Depends(get_config_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> GenerateResponse:
    """Generate menu using the default profile."""
    return await _start_generation(gen_service, config_service, settings_svc, "default", credentials, logger)


# IMPORTANT: /generate/custom must come before /generate/{profile}
# so that "custom" is not captured as a profile name.
@router.post("/generate/custom", status_code=202, response_model=GenerateResponse)
async def generate_custom(
    request: GenerateRequest,
    gen_service: GenerationService = Depends(get_generation_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> GenerateResponse:
    """Generate menu with inline constraints."""
    if gen_service.get_status().state == GenerationState.GENERATING:
        raise HTTPException(status_code=409, detail="A generation is already in progress")

    config = request.model_dump()
    url, token = credentials
    request_id = await gen_service.start_generation(config=config, url=url, token=token, logger=logger, profile_name="custom")
    return GenerateResponse(request_id=request_id, status="generating")


@router.post("/generate/{profile}", status_code=202, response_model=GenerateResponse)
async def generate_profile(
    profile: str,
    gen_service: GenerationService = Depends(get_generation_service),
    config_service: ConfigService = Depends(get_config_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> GenerateResponse:
    """Generate menu using a named profile."""
    return await _start_generation(gen_service, config_service, settings_svc, profile, credentials, logger)


async def _start_generation(
    gen_service: GenerationService,
    config_service: ConfigService,
    settings_svc: SettingsService,
    profile_name: str,
    credentials: tuple[str, str],
    logger: Logger,
) -> GenerateResponse:
    if gen_service.get_status().state == GenerationState.GENERATING:
        raise HTTPException(status_code=409, detail="A generation is already in progress")

    try:
        config = config_service.load_profile(profile_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found") from None

    # Use global cache setting instead of per-profile value
    app_settings = settings_svc.get_all()
    config["cache"] = app_settings.get("api_cache_minutes", API_CACHE_TTL_MINUTES)

    url, token = credentials
    request_id = await gen_service.start_generation(config=config, url=url, token=token, logger=logger, profile_name=profile_name)
    return GenerateResponse(request_id=request_id, status="generating")
