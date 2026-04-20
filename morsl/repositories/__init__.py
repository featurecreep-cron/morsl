"""Repository layer — thin data access over SQLite."""

from __future__ import annotations

from morsl.repositories.history import HistoryRepository
from morsl.repositories.menu import MenuRepository
from morsl.repositories.profile import ProfileRepository
from morsl.repositories.settings import SettingsRepository
from morsl.repositories.template import TemplateRepository
from morsl.repositories.weekly_plan import WeeklyPlanRepository

__all__ = [
    "HistoryRepository",
    "MenuRepository",
    "ProfileRepository",
    "SettingsRepository",
    "TemplateRepository",
    "WeeklyPlanRepository",
]
