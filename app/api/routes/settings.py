from __future__ import annotations

import base64
import hmac
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, HttpUrl, field_validator

from app.api.dependencies import (
    create_admin_token,
    get_category_service,
    get_config_service,
    get_generation_service,
    get_history_service,
    get_scheduler_service,
    get_settings,
    get_settings_service,
    require_admin,
    reset_all_singletons,
    reset_credential_singletons,
    revoke_admin_tokens,
)
from app.config import Settings
from constants import BRANDING_IMAGE_MAX_SIZE, DEFAULT_FAVICON_PATH, ICONS_DIR, UPLOADS_DIR
from services.category_service import CategoryService
from services.config_service import ConfigService
from services.settings_service import DEFAULTS, SettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}


class PinRequest(BaseModel):
    pin: str


class CredentialRequest(BaseModel):
    url: HttpUrl
    token: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Token must not be empty")
        return v.strip()


# Keys that must go through the /credentials endpoint, not PUT /settings
_CREDENTIAL_KEYS = {"tandoor_url", "tandoor_token_b64"}


def _has_credentials(settings: Settings, svc: SettingsService) -> bool:
    """Check if Tandoor credentials exist (ENV or settings.json)."""
    if settings.tandoor_url and settings.tandoor_token:
        return True
    all_s = svc.get_all()
    return bool(all_s.get("tandoor_url") and all_s.get("tandoor_token_b64"))


def _mask_secrets(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Replace secret values with boolean flags."""
    result = dict(settings)
    result["has_pin"] = bool(result.pop("kiosk_pin", ""))
    result["has_tandoor_token"] = bool(result.pop("tandoor_token_b64", ""))
    return result


def require_admin_or_first_run(
    request: Request,
    settings: Settings = Depends(get_settings),
    svc: SettingsService = Depends(get_settings_service),
) -> None:
    """Allow unauthenticated access during first-run; otherwise require admin."""
    if _has_credentials(settings, svc):
        return require_admin(request, svc)
    # First-run: allow through


@router.get("", dependencies=[Depends(require_admin)])
def get_all_settings(svc: SettingsService = Depends(get_settings_service)) -> Dict[str, Any]:
    """Return all settings (admin)."""
    return _mask_secrets(svc.get_all())


@router.put("", dependencies=[Depends(require_admin)])
def update_settings(
    body: Dict[str, Any],
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Update settings (admin)."""
    # 400 (not 422): this is semantic key validation, not Pydantic schema failure
    unknown = set(body.keys()) - set(DEFAULTS.keys())
    if unknown:
        raise HTTPException(400, f"Unknown settings keys: {', '.join(sorted(unknown))}")
    # Credential keys must go through POST /credentials
    cred_in_body = set(body.keys()) & _CREDENTIAL_KEYS
    if cred_in_body:
        raise HTTPException(400, f"Use POST /settings/credentials for: {', '.join(sorted(cred_in_body))}")
    # Revoke tokens if PIN value is actually changing
    if "kiosk_pin" in body:
        current_pin = svc.get_all().get("kiosk_pin", "")
        if body["kiosk_pin"] != current_pin:
            revoke_admin_tokens()
    return _mask_secrets(svc.update(body))


@router.get("/public")
def get_public_settings(svc: SettingsService = Depends(get_settings_service)) -> Dict[str, Any]:
    """Return customer-visible settings only."""
    return svc.get_public()


@router.post("/verify-pin")
def verify_pin(
    body: PinRequest,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Verify admin/kiosk PIN. Returns valid=true and a session token on success."""
    settings = svc.get_all()
    if not (settings.get("admin_pin_enabled") or (settings.get("kiosk_enabled") and settings.get("kiosk_pin_enabled"))):
        return {"valid": True}
    stored_pin = settings.get("kiosk_pin", "")
    if not stored_pin:
        return {"valid": True}
    valid = hmac.compare_digest(body.pin, stored_pin)
    if valid:
        return {"valid": True, "token": create_admin_token()}
    return {"valid": False}


@router.get("/setup-status")
def get_setup_status(
    settings: Settings = Depends(get_settings),
    svc: SettingsService = Depends(get_settings_service),
    config_svc: ConfigService = Depends(get_config_service),
    cat_svc: CategoryService = Depends(get_category_service),
) -> Dict[str, Any]:
    """Check whether initial setup is needed (no auth required)."""
    has_creds = _has_credentials(settings, svc)
    has_env_creds = bool(settings.tandoor_url and settings.tandoor_token)
    has_profiles = len(config_svc.list_profiles()) > 0
    has_categories = len(cat_svc.list_categories()) > 0
    return {
        "needs_setup": not has_creds or not has_profiles,
        "has_credentials": has_creds,
        "has_env_credentials": has_env_creds,
        "has_profiles": has_profiles,
        "has_categories": has_categories,
    }


@router.post("/test-connection", dependencies=[Depends(require_admin_or_first_run)])
async def test_connection(body: CredentialRequest) -> Dict[str, Any]:
    """Test a Tandoor API connection with the given credentials."""
    url = str(body.url).rstrip("/")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{url}/api/food/?limit=1",
                headers={"Authorization": f"Bearer {body.token}"},
                timeout=10,
            )
        if resp.status_code < 400:
            return {"success": True}
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timed out"}
    except Exception as e:
        logger.warning("test-connection failed for %s: %s", url, e)
        return {"success": False, "error": "Connection failed"}


@router.post("/credentials", dependencies=[Depends(require_admin_or_first_run)])
def save_credentials(
    body: CredentialRequest,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Save Tandoor credentials (base64-encoded token) to settings."""
    url = str(body.url).rstrip("/")
    token_b64 = base64.b64encode(body.token.encode()).decode()
    svc.update({"tandoor_url": url, "tandoor_token_b64": token_b64})
    reset_credential_singletons()
    return {"saved": True}


def _save_upload(file: UploadFile, prefix: str) -> str:
    """Validate and save an uploaded image. Returns the public URL path."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Read and check size
    content = file.file.read()
    if len(content) > BRANDING_IMAGE_MAX_SIZE:
        raise HTTPException(400, f"File too large (max {BRANDING_IMAGE_MAX_SIZE // 1024 // 1024}MB)")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{int(time.time())}{ext}"
    dest = UPLOADS_DIR / filename

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=str(UPLOADS_DIR), suffix=".tmp")
    closed = False
    try:
        os.write(fd, content)
        os.close(fd)
        closed = True
        os.replace(tmp_path, str(dest))
    except Exception:
        if not closed:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return f"/uploads/branding/{filename}"


def _remove_uploads(prefix: str) -> None:
    """Remove all uploaded files matching prefix."""
    if UPLOADS_DIR.is_dir():
        for f in UPLOADS_DIR.iterdir():
            if f.name.startswith(prefix + "-"):
                f.unlink(missing_ok=True)


@router.post("/upload/logo", dependencies=[Depends(require_admin)])
def upload_logo(
    file: UploadFile,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Upload a logo image."""
    _remove_uploads("logo")
    url = _save_upload(file, "logo")
    return svc.update({"logo_url": url})


@router.delete("/upload/logo", dependencies=[Depends(require_admin)])
def remove_logo(
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Remove custom logo, revert to default."""
    _remove_uploads("logo")
    return svc.update({"logo_url": ""})


@router.post("/upload/favicon", dependencies=[Depends(require_admin)])
def upload_favicon(
    file: UploadFile,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Upload a favicon source and regenerate all icon variants."""
    _remove_uploads("favicon-source")
    url = _save_upload(file, "favicon-source")

    # Regenerate icons from uploaded source
    source_path = UPLOADS_DIR / url.split("/")[-1]
    try:
        from services.icon_service import generate_icons

        generate_icons(source_path, ICONS_DIR)
        logger.info("Regenerated icons from %s", source_path)
    except Exception as e:
        logger.error("Icon generation failed: %s", e)
        raise HTTPException(500, f"Icon generation failed: {e}") from None

    return svc.update({"favicon_url": url})


@router.delete("/upload/favicon", dependencies=[Depends(require_admin)])
def remove_favicon(
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Remove custom favicon and regenerate from default SVG."""
    _remove_uploads("favicon-source")

    # Regenerate from default
    default_svg = DEFAULT_FAVICON_PATH
    if default_svg.exists():
        try:
            from services.icon_service import generate_icons

            generate_icons(default_svg, ICONS_DIR)
        except Exception as e:
            logger.warning("Default icon regeneration failed: %s", e)

    return svc.update({"favicon_url": ""})


@router.post("/upload/loading-icon", dependencies=[Depends(require_admin)])
def upload_loading_icon(
    file: UploadFile,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Upload a custom loading/waiting icon."""
    _remove_uploads("loading-icon")
    url = _save_upload(file, "loading-icon")
    return svc.update({"loading_icon_url": url})


@router.delete("/upload/loading-icon", dependencies=[Depends(require_admin)])
def remove_loading_icon(
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Remove custom loading icon, revert to default."""
    _remove_uploads("loading-icon")
    return svc.update({"loading_icon_url": ""})


@router.post("/reset-branding", dependencies=[Depends(require_admin)])
def reset_branding(
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Reset all branding to defaults."""
    # Remove all uploaded files
    _remove_uploads("logo")
    _remove_uploads("favicon-source")
    _remove_uploads("loading-icon")

    # Regenerate icons from default favicon
    if DEFAULT_FAVICON_PATH.exists():
        try:
            from services.icon_service import generate_icons

            generate_icons(DEFAULT_FAVICON_PATH, ICONS_DIR)
        except Exception as e:
            logger.warning("Default icon regeneration failed: %s", e)

    # Reset branding settings to defaults
    branding_keys = ["app_name", "slogan_header", "slogan_footer", "logo_url", "favicon_url", "loading_icon_url", "favicon_use_logo", "loading_icon_use_logo", "show_logo"]
    updates = {k: DEFAULTS[k] for k in branding_keys}
    return svc.update(updates)


@router.post("/factory-reset", dependencies=[Depends(require_admin)])
def factory_reset(
    settings: Settings = Depends(get_settings),
    svc: SettingsService = Depends(get_settings_service),
    config_svc: ConfigService = Depends(get_config_service),
    category_svc: CategoryService = Depends(get_category_service),
) -> Dict[str, str]:
    """Erase all server-side data and return to first-run state."""
    errors = []

    # 1. Delete all profiles
    try:
        for p in config_svc.list_profiles():
            try:
                config_svc.delete_profile(p.name)
            except Exception:
                pass
    except Exception as e:
        errors.append(f"profiles: {e}")

    # 2. Delete all categories
    try:
        for cat in category_svc.list_categories():
            try:
                category_svc.delete_category(cat["id"])
            except Exception:
                pass
    except Exception as e:
        errors.append(f"categories: {e}")

    # 3. Delete all schedules
    try:
        scheduler_svc = get_scheduler_service(settings)
        for sched in scheduler_svc.list_schedules():
            try:
                scheduler_svc.delete_schedule(sched["id"])
            except Exception:
                pass
    except Exception as e:
        errors.append(f"schedules: {e}")

    # 4. Clear generation history
    try:
        history_svc = get_history_service(settings)
        history_svc.clear()
    except Exception as e:
        errors.append(f"history: {e}")

    # 5. Clear current menu
    try:
        gen_svc = get_generation_service(settings)
        gen_svc.clear_menu()
    except Exception as e:
        errors.append(f"menu: {e}")

    # 6. Remove branding uploads
    _remove_uploads("logo")
    _remove_uploads("favicon-source")
    _remove_uploads("loading-icon")

    # 7. Delete icon mappings
    try:
        icon_mappings_path = Path(settings.data_dir) / "icon-mappings.json"
        if icon_mappings_path.exists():
            icon_mappings_path.unlink()
    except Exception as e:
        errors.append(f"icon-mappings: {e}")

    # 8. Regenerate default favicon icons
    if DEFAULT_FAVICON_PATH.exists():
        try:
            from services.icon_service import generate_icons

            generate_icons(DEFAULT_FAVICON_PATH, ICONS_DIR)
        except Exception as e:
            logger.warning("Default icon regeneration failed: %s", e)

    # 9. Reset settings.json to defaults (wipe credentials + all settings)
    try:
        settings_path = Path(settings.data_dir) / "settings.json"
        if settings_path.exists():
            settings_path.write_text("{}")
    except Exception as e:
        errors.append(f"settings: {e}")

    # 10. Reset all singleton services so they pick up clean state
    reset_all_singletons()
    revoke_admin_tokens()

    if errors:
        logger.warning("Factory reset completed with errors: %s", errors)

    return {"status": "ok"}
