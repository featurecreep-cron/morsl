from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.dependencies import get_custom_icon_service, require_admin
from constants import CUSTOM_ICON_MAX_SIZE
from services.custom_icon_service import CustomIconService


class IconRenameRequest(BaseModel):
    name: str


router = APIRouter(prefix="/custom-icons", tags=["custom-icons"])


@router.get("")
def list_custom_icons(svc: CustomIconService = Depends(get_custom_icon_service)):
    return svc.list_icons()


@router.post("", dependencies=[Depends(require_admin)])
async def upload_custom_icon(
    file: UploadFile,
    svc: CustomIconService = Depends(get_custom_icon_service),
):
    if not file.filename or not file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only SVG files are accepted")
    content = await file.read()
    if len(content) > CUSTOM_ICON_MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large (max {CUSTOM_ICON_MAX_SIZE // 1024}KB)")
    try:
        result = svc.save_icon(file.filename, content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SVG: {e}")
    return result


@router.get("/all")
def get_all_custom_icons(svc: CustomIconService = Depends(get_custom_icon_service)):
    return svc.get_all_svgs()


@router.get("/{name}/svg")
def get_custom_icon_svg(
    name: str,
    svc: CustomIconService = Depends(get_custom_icon_service),
):
    try:
        svg = svc.get_svg(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Icon not found")
    return Response(content=svg, media_type="image/svg+xml")


@router.patch("/{name}", dependencies=[Depends(require_admin)])
def rename_custom_icon(
    name: str,
    body: IconRenameRequest,
    svc: CustomIconService = Depends(get_custom_icon_service),
):
    new_name = body.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New name is required")
    try:
        return svc.rename_icon(name, new_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Icon not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}", dependencies=[Depends(require_admin)])
def delete_custom_icon(
    name: str,
    svc: CustomIconService = Depends(get_custom_icon_service),
):
    try:
        svc.delete_icon(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Icon not found")
    return {"status": "deleted"}
