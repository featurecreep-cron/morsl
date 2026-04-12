from __future__ import annotations

import base64
import contextlib
import ipaddress
import logging
import os
import socket
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, HttpUrl, field_validator

from morsl.app.api.dependencies import (
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
from morsl.app.config import Settings
from morsl.constants import BRANDING_IMAGE_MAX_SIZE, DEFAULT_FAVICON_PATH, ICONS_DIR, UPLOADS_DIR
from morsl.services.category_service import CategoryService
from morsl.services.config_service import ConfigService
from morsl.services.settings_service import DEFAULTS, SettingsService
from morsl.utils import hash_pin, is_pin_hashed
from morsl.utils import verify_pin as verify_pin_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _reject_private_url(url: str) -> Optional[str]:
    """Return an error message if the URL resolves to a private/internal address, else None."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return "Invalid URL"
    try:
        resolved = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
        for _family, _type, _proto, _canonname, sockaddr in resolved:
            addr = ipaddress.ip_address(sockaddr[0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return "URL must not point to internal/private addresses"
    except (socket.gaierror, OSError):
        return "Could not resolve hostname"
    return None


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
    result["has_pin"] = bool(result.pop("pin", ""))
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
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Update settings (admin)."""
    # 400 (not 422): this is semantic key validation, not Pydantic schema failure
    unknown = set(body.keys()) - set(DEFAULTS.keys())
    if unknown:
        raise HTTPException(400, f"Unknown settings keys: {', '.join(sorted(unknown))}")
    # Credential keys must go through POST /credentials
    cred_in_body = set(body.keys()) & _CREDENTIAL_KEYS
    if cred_in_body:
        raise HTTPException(
            400, f"Use POST /settings/credentials for: {', '.join(sorted(cred_in_body))}"
        )
    # Hash and store PIN if it's being changed
    if "pin" in body:
        new_pin = body["pin"]
        current = svc.get_all()
        stored_pin = current.get("pin", "")
        pin_changed = not new_pin or not verify_pin_hash(new_pin, stored_pin)
        if new_pin:
            body["pin"] = hash_pin(new_pin)
        if pin_changed:
            revoke_admin_tokens()
    result = svc.update(body)
    return _mask_secrets(result)


@router.get("/public")
def get_public_settings(svc: SettingsService = Depends(get_settings_service)) -> Dict[str, Any]:
    """Return customer-visible settings only."""
    return svc.get_public()


_pin_failures: Dict[str, list] = {}  # ip -> [timestamp, ...]
_PIN_RATE_WINDOW = 60  # seconds
_PIN_MAX_ATTEMPTS = 5


def _check_pin_rate_limit(client_ip: str) -> None:
    """Raise 429 if too many failed PIN attempts from this IP."""
    now = time.time()
    attempts = _pin_failures.get(client_ip, [])
    # Prune old attempts outside the window
    attempts = [t for t in attempts if now - t < _PIN_RATE_WINDOW]
    _pin_failures[client_ip] = attempts
    if len(attempts) >= _PIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {_PIN_RATE_WINDOW} seconds.",
        )


def _record_pin_failure(client_ip: str) -> None:
    _pin_failures.setdefault(client_ip, []).append(time.time())


@router.post("/verify-pin")
def verify_pin(
    body: PinRequest,
    request: Request,
    svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Verify admin/kiosk PIN. Returns valid=true and a session token on success."""
    settings = svc.get_all()
    if not (
        settings.get("admin_pin_enabled")
        or (settings.get("kiosk_enabled") and settings.get("kiosk_pin_enabled"))
    ):
        return {"valid": True}
    stored_pin = settings.get("pin", "")
    if not stored_pin:
        return {"valid": True}

    client_ip = request.client.host if request.client else "unknown"
    _check_pin_rate_limit(client_ip)

    valid = verify_pin_hash(body.pin, stored_pin)
    if valid:
        # Transparently migrate plaintext PINs to hashed storage
        if not is_pin_hashed(stored_pin):
            svc.update({"pin": hash_pin(body.pin)})
        # Clear failures on success
        _pin_failures.pop(client_ip, None)
        return {"valid": True, "token": create_admin_token()}
    _record_pin_failure(client_ip)
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
    # SSRF protection: resolve hostname and reject internal/loopback addresses
    _err = _reject_private_url(url)
    if _err:
        return {"success": False, "error": _err}

    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
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
    except (httpx.HTTPError, OSError) as e:
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
        raise HTTPException(
            400, f"File too large (max {BRANDING_IMAGE_MAX_SIZE // 1024 // 1024}MB)"
        )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{int(time.time())}{ext}"
    dest = UPLOADS_DIR / filename

    # Sanitize SVG uploads to prevent stored XSS
    if ext == ".svg":
        try:
            from defusedxml.ElementTree import fromstring

            fromstring(content)  # reject malformed/malicious XML
            from py_svg_hush import filter_svg

            content = filter_svg(content)
        except (ValueError, SyntaxError, OSError):
            raise HTTPException(400, "Invalid or unsafe SVG content") from None

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=str(UPLOADS_DIR), suffix=".tmp")
    closed = False
    try:
        os.write(fd, content)
        os.close(fd)
        closed = True
        os.replace(tmp_path, str(dest))
    except OSError:
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
        from morsl.services.icon_service import generate_icons

        generate_icons(source_path, ICONS_DIR)
        logger.info("Regenerated icons from %s", source_path)
    except (OSError, ValueError) as e:
        logger.error("Icon generation failed: %s", e)
        raise HTTPException(500, "Icon generation failed") from None

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
            from morsl.services.icon_service import generate_icons

            generate_icons(default_svg, ICONS_DIR)
        except (OSError, ValueError) as e:
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
            from morsl.services.icon_service import generate_icons

            generate_icons(DEFAULT_FAVICON_PATH, ICONS_DIR)
        except (OSError, ValueError) as e:
            logger.warning("Default icon regeneration failed: %s", e)

    # Reset branding settings to defaults
    branding_keys = [
        "app_name",
        "slogan_header",
        "slogan_footer",
        "logo_url",
        "favicon_url",
        "loading_icon_url",
        "favicon_use_logo",
        "loading_icon_use_logo",
        "show_logo",
    ]
    updates = {k: DEFAULTS[k] for k in branding_keys}
    return svc.update(updates)


def _reset_step(errors: list, label: str, fn) -> None:
    """Run a factory reset step, collecting errors instead of raising."""
    try:
        fn()
    except Exception as e:  # noqa: broad-except — error collection during factory reset
        errors.append(f"{label}: {e}")


def _delete_all_items(list_fn, delete_fn, id_fn) -> None:
    """Delete all items from a service, suppressing per-item errors."""
    for item in list_fn():
        with contextlib.suppress(Exception):
            delete_fn(id_fn(item))


def _delete_file_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _regenerate_default_icons() -> None:
    if DEFAULT_FAVICON_PATH.exists():
        from morsl.services.icon_service import generate_icons

        generate_icons(DEFAULT_FAVICON_PATH, ICONS_DIR)


@router.post("/factory-reset", dependencies=[Depends(require_admin)])
def factory_reset(
    settings: Settings = Depends(get_settings),
    svc: SettingsService = Depends(get_settings_service),
    config_svc: ConfigService = Depends(get_config_service),
    category_svc: CategoryService = Depends(get_category_service),
) -> Dict[str, str]:
    """Erase all server-side data and return to first-run state."""
    errors: list = []
    data_dir = Path(settings.data_dir)

    _reset_step(
        errors,
        "profiles",
        lambda: _delete_all_items(
            config_svc.list_profiles,
            config_svc.delete_profile,
            lambda p: p.name,
        ),
    )
    _reset_step(
        errors,
        "categories",
        lambda: _delete_all_items(
            category_svc.list_categories,
            category_svc.delete_category,
            lambda c: c["id"],
        ),
    )
    _reset_step(
        errors,
        "schedules",
        lambda: _delete_all_items(
            get_scheduler_service(settings).list_schedules,
            get_scheduler_service(settings).delete_schedule,
            lambda s: s["id"],
        ),
    )
    _reset_step(errors, "history", lambda: get_history_service(settings).clear())
    _reset_step(errors, "menu", lambda: get_generation_service(settings).clear_menu())

    _remove_uploads("logo")
    _remove_uploads("favicon-source")
    _remove_uploads("loading-icon")

    _reset_step(
        errors,
        "icon-mappings",
        lambda: _delete_file_if_exists(
            data_dir / "icon-mappings.json",
        ),
    )
    _reset_step(errors, "icons", _regenerate_default_icons)

    def _clear_settings():
        path = data_dir / "settings.json"
        if path.exists():
            path.write_text("{}")

    _reset_step(errors, "settings", _clear_settings)

    reset_all_singletons()
    revoke_admin_tokens()

    if errors:
        logger.warning("Factory reset completed with errors: %s", errors)

    return {"status": "ok"}
