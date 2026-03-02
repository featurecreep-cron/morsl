from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from app.api.dependencies import (
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
from app.api.routes import api_router
from constants import GENERATION_SHUTDOWN_TIMEOUT, GZIP_MIN_SIZE, ICONS_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Server starting up")
    settings = get_settings()

    # Ensure data directories exist
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    Path(settings.profiles_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "templates").mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir, "weekly_plans").mkdir(parents=True, exist_ok=True)

    # Generate icons on startup if favicon.svg is missing (fresh container)
    icons_dir = ICONS_DIR
    if not (icons_dir / "favicon.svg").exists():
        try:
            from services.icon_service import generate_icons

            settings_svc = get_settings_service(settings)
            current = settings_svc.get_all()
            favicon_url = current.get("favicon_url")
            if favicon_url:
                if favicon_url.startswith("/uploads/branding/"):
                    source = UPLOADS_DIR / favicon_url.split("/")[-1]
                else:
                    source = (Path("web") / favicon_url.lstrip("/")).resolve()
                    web_root = Path("web").resolve()
                    if not str(source).startswith(str(web_root)):
                        logger.warning("favicon_url points outside web/: %s", favicon_url)
                        source = icons_dir / "default-favicon.svg"
            else:
                source = icons_dir / "default-favicon.svg"
            if source.exists():
                generate_icons(source, icons_dir)
                logger.info("Generated startup icons from %s", source)
        except Exception as e:
            logger.warning("Startup icon generation failed (non-fatal): %s", e)

    # Start scheduler
    try:
        scheduler_svc = get_scheduler_service(settings)

        async def generation_callback(profile: str) -> None:
            try:
                gen_svc = get_generation_service(settings)
                app_logger = get_logger(settings)
                config_service = get_config_service(settings)
                config = config_service.load_profile(profile)
                settings_svc = get_settings_service(settings)
                url, token = resolve_credentials(settings, settings_svc)
                await gen_svc.start_generation(
                    config=config,
                    url=url,
                    token=token,
                    logger=app_logger,
                )
                # Wait for generation to complete so downstream steps can use the result
                await gen_svc.wait_for_completion()
            except Exception as e:
                logger.warning(f"Scheduled generation failed for profile '{profile}': {e}")

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
            except Exception as e:
                logger.warning(f"Scheduled weekly generation failed for '{template_name}': {e}")

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
            except Exception as e:
                logger.warning(f"Scheduled weekly save failed (non-fatal): {e}")

        scheduler_svc.set_generation_callback(generation_callback)
        scheduler_svc.set_clear_callback(get_generation_service(settings).clear_menu)
        scheduler_svc.set_meal_plan_callback(meal_plan_callback)
        scheduler_svc.set_weekly_generation_callback(weekly_generation_callback)
        scheduler_svc.set_weekly_save_callback(weekly_save_callback)
        scheduler_svc.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler startup failed (non-fatal): {e}")

    yield

    # Shutdown — cancel any in-flight generation tasks
    logger.info("Server shutting down, cancelling background tasks...")
    try:
        gen_service = get_generation_service(settings)
        await gen_service.shutdown(timeout=GENERATION_SHUTDOWN_TIMEOUT)
    except Exception as e:
        logger.warning(f"Error during shutdown cleanup: {e}")

    try:
        weekly_gen_service = get_weekly_generation_service(settings)
        await weekly_gen_service.shutdown(timeout=GENERATION_SHUTDOWN_TIMEOUT)
    except Exception as e:
        logger.warning(f"Weekly generation shutdown error: {e}")

    # Stop scheduler
    try:
        scheduler_svc = get_scheduler_service(settings)
        scheduler_svc.stop()
    except Exception as e:
        logger.warning(f"Scheduler shutdown error: {e}")

    logger.info("Shutdown complete")


app = FastAPI(
    title="Morsl",
    description="API for generating menus from Tandoor recipes\n\n[Back to Admin](/admin) | [Menu](/)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE)


@app.middleware("http")
async def no_cache_static_assets(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".css", ".js", ".html")) or request.url.path in ("/", "/admin", "/setup"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.include_router(api_router)


@app.get("/health")
def health_check(
    settings=Depends(get_settings),
    settings_svc=Depends(get_settings_service),
    scheduler=Depends(get_scheduler_service),
) -> dict:
    # Check credentials from env or settings.json
    has_env_creds = bool(settings.tandoor_url and settings.tandoor_token)
    if not has_env_creds:
        all_s = settings_svc.get_all()
        has_ui_creds = bool(all_s.get("tandoor_url") and all_s.get("tandoor_token_b64"))
    else:
        has_ui_creds = False

    # Check scheduler
    try:
        scheduler_running = scheduler.is_running
    except Exception:
        scheduler_running = False

    return {
        "status": "ok",
        "credentials_configured": has_env_creds or has_ui_creds,
        "scheduler_running": scheduler_running,
    }


def _needs_setup() -> bool:
    """Check if first-run setup is needed (no credentials or no profiles)."""
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
    app.mount("/uploads/branding", StaticFiles(directory=str(UPLOADS_DIR)), name="branding")
except (FileNotFoundError, RuntimeError):
    logger.info("data/branding/ mount skipped — directory not available")

# Mount static files for future frontend — API routes take priority
try:
    app.mount("/", StaticFiles(directory="web", html=True), name="web")
except (FileNotFoundError, RuntimeError):
    logger.info("web/ directory not found — static file serving disabled")
