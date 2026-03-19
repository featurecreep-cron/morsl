from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from morsl.app.api.dependencies import (
    get_config_service,
    get_generation_service,
    get_logger,
    get_meal_plan_service,
    get_scheduler_service,
    get_settings,
    get_settings_service,
    get_template_service,
    get_weekly_generation_service,
    resolve_credentials,
)
from morsl.app.api.routes import api_router
from morsl.constants import GENERATION_SHUTDOWN_TIMEOUT, GZIP_MIN_SIZE, ICONS_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)


class _HealthCheckFilter(logging.Filter):
    """Suppress access-log entries for /health to avoid log spam from Docker healthchecks."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return '"GET /health' not in msg


def _ensure_data_dirs(settings) -> None:
    """Create data directories if they don't exist."""
    for d in [
        UPLOADS_DIR,
        Path(settings.profiles_dir),
        Path(settings.data_dir, "templates"),
        Path(settings.data_dir, "weekly_plans"),
    ]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning(
                "Cannot create %s — check volume ownership (needs UID 1000)",
                d,
            )


def _generate_startup_icons(settings) -> None:
    """Generate icons on first boot if favicon.svg is missing."""
    icons_dir = ICONS_DIR
    if (icons_dir / "favicon.svg").exists():
        return
    try:
        from morsl.services.icon_service import generate_icons

        settings_svc = get_settings_service(settings)
        current = settings_svc.get_all()
        source = _resolve_favicon_source(current.get("favicon_url"), icons_dir)
        if source.exists():
            generate_icons(source, icons_dir)
            logger.info("Generated startup icons from %s", source)
    except Exception as e:
        logger.warning("Startup icon generation failed (non-fatal): %s", e)


def _resolve_favicon_source(favicon_url, icons_dir: Path) -> Path:
    """Determine the source file for favicon generation."""
    if not favicon_url:
        return icons_dir / "default-favicon.svg"
    if favicon_url.startswith("/uploads/branding/"):
        return UPLOADS_DIR / favicon_url.split("/")[-1]
    source = (Path("web") / favicon_url.lstrip("/")).resolve()
    web_root = Path("web").resolve()
    if not source.is_relative_to(web_root):
        logger.warning("favicon_url points outside web/: %s", favicon_url)
        return icons_dir / "default-favicon.svg"
    return source


def _build_scheduler_callbacks(settings):
    """Create the callback functions for the scheduler service."""

    async def generation_callback(profile: str) -> None:
        try:
            gen_svc = get_generation_service(settings)
            app_logger = get_logger(settings)
            config_service = get_config_service(settings)
            config = config_service.load_profile(profile)
            settings_svc = get_settings_service(settings)
            url, token = resolve_credentials(settings, settings_svc)
            await gen_svc.start_generation(config=config, url=url, token=token, logger=app_logger)
            await gen_svc.wait_for_completion()
        except Exception:
            logger.warning(
                "Scheduled generation failed for profile '%s'",
                profile,
                exc_info=True,
            )

    async def meal_plan_callback(action: str, params: dict) -> None:
        """Handle meal plan pipeline actions dispatched by the scheduler."""
        settings_svc = get_settings_service(settings)
        meal_plan_svc = get_meal_plan_service(settings, settings_svc)
        if action == "cleanup":
            await asyncio.to_thread(
                meal_plan_svc.cleanup,
                meal_plan_type=params["meal_plan_type"],
                days=params["cleanup_days"],
            )
        elif action == "create":
            gen_svc = get_generation_service(settings)
            menu = gen_svc.get_current_menu()
            if not menu or not menu.get("recipes"):
                logger.warning("No current menu — skipping meal plan creation")
                return
            await asyncio.to_thread(
                meal_plan_svc.create_from_menu,
                meal_plan_type_id=params["meal_plan_type"],
                recipes=menu["recipes"],
            )

    async def weekly_generation_callback(template_name: str, week_start=None) -> None:
        try:
            weekly_svc = get_weekly_generation_service(settings)
            template_svc = get_template_service(settings)
            config_svc = get_config_service(settings)
            app_logger = get_logger(settings)
            settings_svc = get_settings_service(settings)
            gen_svc = get_generation_service(settings)
            url, token = resolve_credentials(settings, settings_svc)
            await weekly_svc.start_generation(
                template_name=template_name,
                template_service=template_svc,
                config_service=config_svc,
                url=url,
                token=token,
                app_logger=app_logger,
                week_start=week_start,
                generation_service=gen_svc,
                settings_service=settings_svc,
            )
            await weekly_svc.wait_for_completion()
        except Exception:
            logger.warning(
                "Scheduled weekly generation failed for '%s'",
                template_name,
                exc_info=True,
            )

    async def weekly_save_callback(template_name: str) -> None:
        try:
            weekly_svc = get_weekly_generation_service(settings)
            plan = weekly_svc.get_plan(template_name)
            if not plan:
                logger.warning("No weekly plan — skipping save to Tandoor")
                return
            settings_svc = get_settings_service(settings)
            meal_plan_svc = get_meal_plan_service(settings, settings_svc)
            await asyncio.to_thread(
                meal_plan_svc.save_weekly_plan,
                weekly_plan=plan,
                shared=[],
            )
        except Exception:
            logger.warning("Scheduled weekly save failed (non-fatal)", exc_info=True)

    return (
        generation_callback,
        meal_plan_callback,
        weekly_generation_callback,
        weekly_save_callback,
    )


def _setup_scheduler(settings) -> None:
    """Wire up scheduler callbacks and start the scheduler."""
    scheduler_svc = get_scheduler_service(settings)
    (
        gen_cb,
        meal_plan_cb,
        weekly_gen_cb,
        weekly_save_cb,
    ) = _build_scheduler_callbacks(settings)

    scheduler_svc.set_generation_callback(gen_cb)
    scheduler_svc.set_clear_callback(get_generation_service(settings).clear_menu)
    scheduler_svc.set_meal_plan_callback(meal_plan_cb)
    scheduler_svc.set_weekly_generation_callback(weekly_gen_cb)
    scheduler_svc.set_weekly_save_callback(weekly_save_cb)
    scheduler_svc.start()
    logger.info("Scheduler started")


async def _shutdown_services(settings) -> None:
    """Gracefully shut down generation services and scheduler."""
    try:
        gen_service = get_generation_service(settings)
        await gen_service.shutdown(timeout=GENERATION_SHUTDOWN_TIMEOUT)
    except Exception:
        logger.warning("Error during shutdown cleanup", exc_info=True)

    try:
        weekly_gen_service = get_weekly_generation_service(settings)
        await weekly_gen_service.shutdown(timeout=GENERATION_SHUTDOWN_TIMEOUT)
    except Exception:
        logger.warning("Weekly generation shutdown error", exc_info=True)

    try:
        scheduler_svc = get_scheduler_service(settings)
        scheduler_svc.stop()
    except Exception:
        logger.warning("Scheduler shutdown error", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting up")

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(_HealthCheckFilter())
    settings = get_settings()

    _ensure_data_dirs(settings)
    _generate_startup_icons(settings)

    try:
        _setup_scheduler(settings)
    except Exception:
        logger.warning("Scheduler startup failed (non-fatal)", exc_info=True)

    yield

    logger.info("Server shutting down, cancelling background tasks...")
    await _shutdown_services(settings)
    logger.info("Shutdown complete")


APP_VERSION = os.environ.get("MORSL_VERSION", "dev")

app = FastAPI(
    title="Morsl",
    description=(
        "API for generating menus from Tandoor recipes" "\n\n[Back to Admin](/admin) | [Menu](/)"
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE)


@app.middleware("http")
async def no_cache_static_assets(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".css", ".js", ".html")) or request.url.path in (
        "/",
        "/admin",
        "/setup",
    ):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.include_router(api_router)


@app.get("/health")
def health_check(
    settings=Depends(get_settings),
    settings_svc=Depends(get_settings_service),
    scheduler=Depends(get_scheduler_service),
) -> dict:
    has_env_creds = bool(settings.tandoor_url and settings.tandoor_token)
    if not has_env_creds:
        all_s = settings_svc.get_all()
        has_ui_creds = bool(all_s.get("tandoor_url") and all_s.get("tandoor_token_b64"))
    else:
        has_ui_creds = False

    try:
        scheduler_running = scheduler.is_running
    except Exception:
        scheduler_running = False

    return {
        "status": "ok",
        "version": APP_VERSION,
        "credentials_configured": has_env_creds or has_ui_creds,
        "scheduler_running": scheduler_running,
    }


def _needs_setup() -> bool:
    """Check if first-run setup is needed."""
    svc = get_settings_service(get_settings())
    settings = get_settings()
    has_env = bool(settings.tandoor_url and settings.tandoor_token)
    if not has_env:
        all_s = svc.get_all()
        has_creds = bool(all_s.get("tandoor_url") and all_s.get("tandoor_token_b64"))
    else:
        has_creds = True
    if not has_creds:
        return True
    config_svc = get_config_service(settings)
    return len(config_svc.list_profiles()) == 0


@app.get("/setup")
@app.get("/setup.html")
def setup_page(request: Request) -> Response:
    if not _needs_setup() and "mode" not in request.query_params:
        return RedirectResponse(url="/admin")
    return FileResponse("web/setup.html")


@app.get("/admin")
@app.get("/admin.html")
def admin_page() -> Response:
    if _needs_setup():
        return RedirectResponse(url="/setup")
    return FileResponse("web/admin.html")


@app.get("/")
@app.get("/index.html")
def index_page() -> Response:
    if _needs_setup():
        return RedirectResponse(url="/setup")
    return FileResponse("web/index.html")


@app.get("/manifest.json")
def dynamic_manifest() -> JSONResponse:
    """Serve manifest.json with dynamic app name from settings."""
    manifest_path = Path("web/manifest.json")
    if not manifest_path.exists():
        return JSONResponse({"error": "manifest not found"}, status_code=404)
    with open(manifest_path) as f:
        manifest = json.load(f)
    svc = get_settings_service(get_settings())
    all_settings = svc.get_all()
    app_name = all_settings.get("app_name") or "Morsl"
    manifest["name"] = app_name
    manifest["short_name"] = app_name
    return JSONResponse(manifest)


# Mount branding uploads from data/branding/ at the existing URL path
try:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/uploads/branding",
        StaticFiles(directory=str(UPLOADS_DIR)),
        name="branding",
    )
except (FileNotFoundError, RuntimeError, PermissionError):
    logger.info("data/branding/ mount skipped — directory not available")

# Mount static files for future frontend — API routes take priority
try:
    app.mount("/", StaticFiles(directory="web", html=True), name="web")
except (FileNotFoundError, RuntimeError):
    logger.info("web/ directory not found — static file serving disabled")
