from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from morsl.app.api.dependencies import get_icon_mapping_service, require_admin
from morsl.app.api.models import IconMappingRequest
from morsl.services.icon_mapping_service import IconMappingService

router = APIRouter(prefix="/icon-mappings", tags=["icon-mappings"])


@router.get("")
def list_icon_mappings(
    svc: IconMappingService = Depends(get_icon_mapping_service),
) -> Dict[str, Any]:
    return svc.get_all()


@router.put("", dependencies=[Depends(require_admin)])
def update_icon_mappings(
    body: IconMappingRequest,
    svc: IconMappingService = Depends(get_icon_mapping_service),
) -> Dict[str, Any]:
    return svc.update(body.keyword_icons, body.food_icons)
