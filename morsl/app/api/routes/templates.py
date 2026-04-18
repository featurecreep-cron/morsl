from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from morsl.app.api.dependencies import get_config_service, get_template_service, require_admin
from morsl.app.api.models import (
    TemplateCreateRequest,
    TemplateDetailResponse,
    TemplateSummaryResponse,
    TemplateUpdateRequest,
)
from morsl.services.config_service import ConfigService
from morsl.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"], dependencies=[Depends(require_admin)])


@router.get("", response_model=List[TemplateSummaryResponse])
def list_templates(
    svc: TemplateService = Depends(get_template_service),
) -> list:
    return svc.list_templates()


@router.post("", response_model=TemplateDetailResponse, status_code=201)
def create_template(
    request: TemplateCreateRequest,
    svc: TemplateService = Depends(get_template_service),
    config_svc: ConfigService = Depends(get_config_service),
) -> dict:
    config = request.model_dump()
    name = config.pop("name")

    errors = svc.validate_template(config, config_svc)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        return svc.create_template(name, config)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template name") from None
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Template already exists") from None


@router.get("/{name}", response_model=TemplateDetailResponse)
def get_template(
    name: str,
    svc: TemplateService = Depends(get_template_service),
) -> dict:
    try:
        return svc.get_template(name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template name") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found") from None


@router.put("/{name}", response_model=TemplateDetailResponse)
def update_template(
    name: str,
    request: TemplateUpdateRequest,
    svc: TemplateService = Depends(get_template_service),
    config_svc: ConfigService = Depends(get_config_service),
) -> dict:
    config = request.model_dump()

    errors = svc.validate_template(config, config_svc)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        return svc.update_template(name, config)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template name") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found") from None


@router.delete("/{name}", status_code=204)
def delete_template(
    name: str,
    svc: TemplateService = Depends(get_template_service),
) -> None:
    try:
        svc.delete_template(name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template name") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found") from None
