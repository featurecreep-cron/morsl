from __future__ import annotations

import base64
import secrets
import threading
from functools import lru_cache
from logging import Logger

import cachetools
from fastapi import Depends, HTTPException, Request

from app.config import Settings
from constants import ADMIN_TOKEN_CACHE_MAXSIZE, ADMIN_TOKEN_CACHE_TTL_SECONDS
from services.category_service import CategoryService
from services.config_service import ConfigService
from services.custom_icon_service import CustomIconService
from services.generation_service import GenerationService
from services.history_service import HistoryService
from services.icon_mapping_service import IconMappingService
from services.meal_plan_service import MealPlanService
from services.order_service import OrderService
from services.scheduler_service import SchedulerService
from services.settings_service import SettingsService
from services.template_service import TemplateService
from services.weekly_generation_service import WeeklyGenerationService
from utils import setup_logging

# Admin token store — bounded size + auto-expiry (24h TTL)
_admin_tokens: cachetools.TTLCache = cachetools.TTLCache(maxsize=ADMIN_TOKEN_CACHE_MAXSIZE, ttl=ADMIN_TOKEN_CACHE_TTL_SECONDS)
_admin_tokens_lock = threading.Lock()

# Service singleton registry — replaces 12 separate global variables
_services: dict[str, object] = {}


def _get_or_create(key: str, factory):
    """Return existing singleton or create via factory."""
    if key not in _services:
        _services[key] = factory()
    return _services[key]


def create_admin_token() -> str:
    """Generate a new admin session token and store it."""
    token = secrets.token_hex(16)
    with _admin_tokens_lock:
        _admin_tokens[token] = True
    return token


def revoke_admin_tokens() -> None:
    """Invalidate all admin tokens (e.g. after PIN change)."""
    with _admin_tokens_lock:
        _admin_tokens.clear()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_config_service(settings: Settings = Depends(get_settings)) -> ConfigService:
    return _get_or_create("config", lambda: ConfigService(profiles_dir=settings.profiles_dir))


def get_history_service(settings: Settings = Depends(get_settings)) -> HistoryService:
    return _get_or_create("history", lambda: HistoryService(data_dir=settings.data_dir))


def get_generation_service(settings: Settings = Depends(get_settings)) -> GenerationService:
    return _get_or_create(
        "generation",
        lambda: GenerationService(data_dir=settings.data_dir, history_service=get_history_service(settings)),
    )


def get_settings_service(settings: Settings = Depends(get_settings)) -> SettingsService:
    return _get_or_create("settings_svc", lambda: SettingsService(data_dir=settings.data_dir))


def resolve_credentials(settings: Settings, settings_svc: SettingsService) -> tuple[str, str]:
    """Resolve Tandoor credentials: ENV vars take priority, then settings.json (base64 token)."""
    if settings.tandoor_url and settings.tandoor_token:
        return settings.tandoor_url, settings.tandoor_token
    all_settings = settings_svc.get_all()
    url = all_settings.get("tandoor_url", "")
    token_b64 = all_settings.get("tandoor_token_b64", "")
    if url and token_b64:
        try:
            token = base64.b64decode(token_b64).decode()
        except Exception:
            raise HTTPException(500, "Stored Tandoor token is corrupt (invalid base64)") from None
        return url, token
    raise HTTPException(500, "TANDOOR_URL and TANDOOR_TOKEN must be configured")


def reset_credential_singletons() -> None:
    """Reset singletons that cache Tandoor credentials so they pick up new values."""
    _services.pop("order", None)
    _services.pop("meal_plan", None)


def reset_all_singletons() -> None:
    """Reset all singleton services (used by factory reset)."""
    _services.clear()


def get_order_service(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> OrderService:
    def _create():
        url, token = resolve_credentials(settings, settings_svc)
        return OrderService(url=url, token=token)

    return _get_or_create("order", _create)


def get_meal_plan_service(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> MealPlanService:
    def _create():
        url, token = resolve_credentials(settings, settings_svc)
        return MealPlanService(
            url=url,
            token=token,
            logger=setup_logging(log=settings.log_level, log_to_stdout=settings.log_to_stdout),
        )

    return _get_or_create("meal_plan", _create)


def get_scheduler_service(settings: Settings = Depends(get_settings)) -> SchedulerService:
    def _create() -> SchedulerService:
        settings_svc = get_settings_service(settings)
        return SchedulerService(
            data_dir=settings.data_dir,
            timezone=settings_svc.get_timezone(),
        )

    return _get_or_create("scheduler", _create)


def require_admin(
    request: Request,
    svc: SettingsService = Depends(get_settings_service),
) -> None:
    """FastAPI dependency: reject requests without a valid admin token.

    When PIN is disabled (neither admin_pin_enabled nor kiosk+kiosk_pin_enabled),
    all requests are allowed through without a token.
    """
    settings = svc.get_all()
    pin_active = settings.get("admin_pin_enabled") or (settings.get("kiosk_enabled") and settings.get("kiosk_pin_enabled"))
    if not pin_active:
        return  # No PIN configured — allow all

    token = request.headers.get("X-Admin-Token", "")
    with _admin_tokens_lock:
        valid = token and token in _admin_tokens
    if not valid:
        raise HTTPException(status_code=401, detail="Admin authentication required")


def get_category_service(settings: Settings = Depends(get_settings)) -> CategoryService:
    return _get_or_create("category", lambda: CategoryService(data_dir=settings.data_dir))


def get_custom_icon_service(settings: Settings = Depends(get_settings)) -> CustomIconService:
    return _get_or_create("custom_icon", lambda: CustomIconService(data_dir=settings.data_dir))


def get_icon_mapping_service(settings: Settings = Depends(get_settings)) -> IconMappingService:
    return _get_or_create("icon_mapping", lambda: IconMappingService(data_dir=settings.data_dir))


def get_template_service(settings: Settings = Depends(get_settings)) -> TemplateService:
    return _get_or_create("template", lambda: TemplateService(data_dir=settings.data_dir))


def get_weekly_generation_service(settings: Settings = Depends(get_settings)) -> WeeklyGenerationService:
    return _get_or_create("weekly_generation", lambda: WeeklyGenerationService(data_dir=settings.data_dir))


def get_logger(settings: Settings = Depends(get_settings)) -> Logger:
    return setup_logging(log=settings.log_level, log_to_stdout=settings.log_to_stdout)


def get_credentials(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> tuple[str, str]:
    return resolve_credentials(settings, settings_svc)
