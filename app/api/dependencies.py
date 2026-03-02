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
_admin_tokens: cachetools.TTLCache = cachetools.TTLCache(
    maxsize=ADMIN_TOKEN_CACHE_MAXSIZE, ttl=ADMIN_TOKEN_CACHE_TTL_SECONDS
)
_admin_tokens_lock = threading.Lock()


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


_config_service: ConfigService | None = None


def get_config_service(settings: Settings = Depends(get_settings)) -> ConfigService:
    global _config_service
    if _config_service is None:
        _config_service = ConfigService(profiles_dir=settings.profiles_dir)
    return _config_service


# Singleton history service
_history_service: HistoryService | None = None


def get_history_service(settings: Settings = Depends(get_settings)) -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService(data_dir=settings.data_dir)
    return _history_service


# Singleton generation service
_generation_service: GenerationService | None = None


def get_generation_service(settings: Settings = Depends(get_settings)) -> GenerationService:
    global _generation_service
    if _generation_service is None:
        history_svc = get_history_service(settings)
        _generation_service = GenerationService(
            data_dir=settings.data_dir, history_service=history_svc
        )
    return _generation_service


# Singleton settings service (must be defined before services that depend on credentials)
_settings_service: SettingsService | None = None


def get_settings_service(settings: Settings = Depends(get_settings)) -> SettingsService:
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService(data_dir=settings.data_dir)
    return _settings_service


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
            raise HTTPException(500, "Stored Tandoor token is corrupt (invalid base64)")
        return url, token
    raise HTTPException(500, "TANDOOR_URL and TANDOOR_TOKEN must be configured")


def reset_credential_singletons() -> None:
    """Reset singletons that cache Tandoor credentials so they pick up new values."""
    global _order_service, _meal_plan_service
    _order_service = None
    _meal_plan_service = None


def reset_all_singletons() -> None:
    """Reset all singleton services (used by factory reset)."""
    global _config_service, _history_service, _generation_service
    global _settings_service, _order_service, _meal_plan_service
    global _scheduler_service, _category_service, _custom_icon_service
    global _icon_mapping_service, _template_service, _weekly_generation_service
    _config_service = None
    _history_service = None
    _generation_service = None
    _settings_service = None
    _order_service = None
    _meal_plan_service = None
    _scheduler_service = None
    _category_service = None
    _custom_icon_service = None
    _icon_mapping_service = None
    _template_service = None
    _weekly_generation_service = None


# Singleton order service
_order_service: OrderService | None = None


def get_order_service(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> OrderService:
    global _order_service
    if _order_service is None:
        url, token = resolve_credentials(settings, settings_svc)
        _order_service = OrderService(url=url, token=token)
    return _order_service


# Singleton meal plan service
_meal_plan_service: MealPlanService | None = None


def get_meal_plan_service(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> MealPlanService:
    global _meal_plan_service
    if _meal_plan_service is None:
        url, token = resolve_credentials(settings, settings_svc)
        _meal_plan_service = MealPlanService(
            url=url,
            token=token,
            logger=setup_logging(log=settings.log_level, log_to_stdout=settings.log_to_stdout),
        )
    return _meal_plan_service


# Singleton scheduler service
_scheduler_service: SchedulerService | None = None


def get_scheduler_service(settings: Settings = Depends(get_settings)) -> SchedulerService:
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService(data_dir=settings.data_dir)
    return _scheduler_service


def require_admin(
    request: Request,
    svc: SettingsService = Depends(get_settings_service),
) -> None:
    """FastAPI dependency: reject requests without a valid admin token.

    When PIN is disabled (neither admin_pin_enabled nor kiosk+kiosk_pin_enabled),
    all requests are allowed through without a token.
    """
    settings = svc.get_all()
    pin_active = settings.get("admin_pin_enabled") or (
        settings.get("kiosk_enabled") and settings.get("kiosk_pin_enabled")
    )
    if not pin_active:
        return  # No PIN configured — allow all

    token = request.headers.get("X-Admin-Token", "")
    with _admin_tokens_lock:
        valid = token and token in _admin_tokens
    if not valid:
        raise HTTPException(status_code=401, detail="Admin authentication required")


# Singleton category service
_category_service: CategoryService | None = None


def get_category_service(settings: Settings = Depends(get_settings)) -> CategoryService:
    global _category_service
    if _category_service is None:
        _category_service = CategoryService(data_dir=settings.data_dir)
    return _category_service


# Singleton custom icon service
_custom_icon_service: CustomIconService | None = None


def get_custom_icon_service(settings: Settings = Depends(get_settings)) -> CustomIconService:
    global _custom_icon_service
    if _custom_icon_service is None:
        _custom_icon_service = CustomIconService(data_dir=settings.data_dir)
    return _custom_icon_service


# Singleton icon mapping service
_icon_mapping_service: IconMappingService | None = None


def get_icon_mapping_service(settings: Settings = Depends(get_settings)) -> IconMappingService:
    global _icon_mapping_service
    if _icon_mapping_service is None:
        _icon_mapping_service = IconMappingService(data_dir=settings.data_dir)
    return _icon_mapping_service


# Singleton template service
_template_service: TemplateService | None = None


def get_template_service(settings: Settings = Depends(get_settings)) -> TemplateService:
    global _template_service
    if _template_service is None:
        _template_service = TemplateService(data_dir=settings.data_dir)
    return _template_service


# Singleton weekly generation service
_weekly_generation_service: WeeklyGenerationService | None = None


def get_weekly_generation_service(settings: Settings = Depends(get_settings)) -> WeeklyGenerationService:
    global _weekly_generation_service
    if _weekly_generation_service is None:
        _weekly_generation_service = WeeklyGenerationService(data_dir=settings.data_dir)
    return _weekly_generation_service


def get_logger(settings: Settings = Depends(get_settings)) -> Logger:
    return setup_logging(log=settings.log_level, log_to_stdout=settings.log_to_stdout)


def get_credentials(
    settings: Settings = Depends(get_settings),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> tuple[str, str]:
    return resolve_credentials(settings, settings_svc)
