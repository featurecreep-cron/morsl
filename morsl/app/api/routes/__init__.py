from __future__ import annotations

from fastapi import APIRouter

from morsl.app.api.routes.categories import router as categories_router
from morsl.app.api.routes.custom_icons import router as custom_icons_router
from morsl.app.api.routes.generation import router as generation_router
from morsl.app.api.routes.history import router as history_router
from morsl.app.api.routes.icon_mappings import router as icon_mappings_router
from morsl.app.api.routes.meal_plan import router as meal_plan_router
from morsl.app.api.routes.menu import router as menu_router
from morsl.app.api.routes.orders import router as orders_router
from morsl.app.api.routes.profiles import router as profiles_router
from morsl.app.api.routes.proxy import router as proxy_router
from morsl.app.api.routes.schedules import router as schedules_router
from morsl.app.api.routes.settings import router as settings_router
from morsl.app.api.routes.shopping import router as shopping_router
from morsl.app.api.routes.templates import router as templates_router
from morsl.app.api.routes.weekly_generation import router as weekly_generation_router

api_router = APIRouter(prefix="/api")
api_router.include_router(categories_router)
api_router.include_router(custom_icons_router)
api_router.include_router(generation_router)
api_router.include_router(history_router)
api_router.include_router(icon_mappings_router)
api_router.include_router(meal_plan_router)
api_router.include_router(menu_router)
api_router.include_router(profiles_router)
api_router.include_router(proxy_router)
api_router.include_router(orders_router)
api_router.include_router(schedules_router)
api_router.include_router(settings_router)
api_router.include_router(shopping_router)
api_router.include_router(templates_router)
api_router.include_router(weekly_generation_router)
