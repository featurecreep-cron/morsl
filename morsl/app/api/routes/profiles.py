from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import (
    get_config_service,
    get_credentials,
    get_settings_service,
    require_admin,
)
from morsl.app.api.models import ProfileCreateRequest, ProfileDetailResponse, ProfileResponse
from morsl.constants import API_CACHE_TTL_MINUTES, DEFAULT_CHOICES
from morsl.services.config_service import ConfigService
from morsl.services.menu_service import MenuService
from morsl.services.settings_service import SettingsService

router = APIRouter(tags=["profiles"])


@router.get("/profiles", response_model=List[ProfileResponse])
def list_profiles(
    config_service: ConfigService = Depends(get_config_service),
) -> List[ProfileResponse]:
    """List available generation profiles."""
    profiles = config_service.list_profiles()
    return [
        ProfileResponse(
            name=p.name,
            choices=p.choices,
            constraint_count=p.constraint_count,
            description=p.description,
            icon=p.icon,
            category=p.category,
            default=p.default,
            show_on_menu=p.show_on_menu,
            item_noun=p.item_noun,
        )
        for p in profiles
    ]


@router.get("/profiles/{name}", response_model=ProfileDetailResponse)
def get_profile(
    name: str,
    config_service: ConfigService = Depends(get_config_service),
) -> ProfileDetailResponse:
    """Get full profile configuration."""
    try:
        config = config_service.get_profile_raw(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}") from None
    if not config:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}")
    return ProfileDetailResponse(name=name, config=config)


@router.post(
    "/profiles",
    response_model=ProfileDetailResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_profile(
    request: ProfileCreateRequest,
    config_service: ConfigService = Depends(get_config_service),
) -> ProfileDetailResponse:
    """Create a new profile."""
    try:
        config = config_service.create_profile(request.name, request.to_config_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    if request.default:
        config_service.set_default_profile(request.name)
    return ProfileDetailResponse(name=request.name, config=config)


@router.put(
    "/profiles/{name}", response_model=ProfileDetailResponse, dependencies=[Depends(require_admin)]
)
def update_profile(
    name: str,
    request: ProfileCreateRequest,
    config_service: ConfigService = Depends(get_config_service),
) -> ProfileDetailResponse:
    """Update an existing profile."""
    try:
        config = config_service.update_profile(name, request.to_config_dict())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}") from None
    if request.default:
        config_service.set_default_profile(name)
    else:
        config_service.clear_default_profile(name)
    return ProfileDetailResponse(name=name, config=config)


@router.patch("/profiles/{name}/category", dependencies=[Depends(require_admin)])
def set_profile_category(
    name: str,
    body: Dict[str, Any],
    config_service: ConfigService = Depends(get_config_service),
) -> Dict[str, str]:
    """Set just the category for a profile."""
    try:
        config = config_service.get_profile_raw(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}") from None
    if not config:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}")
    config["category"] = body.get("category", "")
    config_service.update_profile(name, config)
    return {"status": "ok"}


@router.delete("/profiles/{name}", status_code=204, dependencies=[Depends(require_admin)])
def delete_profile(
    name: str,
    config_service: ConfigService = Depends(get_config_service),
) -> None:
    """Delete a profile."""
    try:
        config_service.delete_profile(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {name}") from None


@router.post("/profiles/preview", dependencies=[Depends(require_admin)])
def preview_profile(
    request: ProfileCreateRequest,
    config_service: ConfigService = Depends(get_config_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    credentials: tuple[str, str] = Depends(get_credentials),
) -> Dict[str, Any]:
    """Preview constraint matching - returns count of recipes that match the constraints."""
    url, token = credentials

    logger = logging.getLogger("menu_preview")
    config = request.to_config_dict()
    config["description"] = request.description  # Preserve description
    config["cache"] = settings_svc.get_all().get("api_cache_minutes", API_CACHE_TTL_MINUTES)

    try:
        service = MenuService(url=url, token=token, config=config, logger=logger)
        service.prepare_data()
        return {
            "matching_count": len(service.recipes),
            "choices": config.get("choices", DEFAULT_CHOICES),
        }
    except Exception as e:
        logger.warning(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
