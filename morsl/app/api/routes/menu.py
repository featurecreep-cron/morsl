from __future__ import annotations

import asyncio
import json
from logging import Logger

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from morsl.app.api.dependencies import (
    get_config_service,
    get_credentials,
    get_generation_service,
    get_logger,
    require_admin,
)
from morsl.app.api.models import (
    GenerationStatusResponse,
    MenuResponse,
    RecipeResponse,
    SwapRequest,
)
from morsl.constants import SSE_QUEUE_TIMEOUT
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationService

router = APIRouter(tags=["menu"])


@router.get("/menu", response_model=MenuResponse)
def get_menu(
    gen_service: GenerationService = Depends(get_generation_service),
) -> MenuResponse:
    """Get the current generated menu."""
    menu_data = gen_service.get_current_menu()
    if menu_data is None:
        raise HTTPException(status_code=404, detail="No menu has been generated yet")
    return MenuResponse(**menu_data)


@router.delete("/menu", status_code=204, dependencies=[Depends(require_admin)])
def delete_menu(
    gen_service: GenerationService = Depends(get_generation_service),
) -> None:
    """Clear the current menu data."""
    gen_service.clear_menu()


@router.get("/status", response_model=GenerationStatusResponse)
def get_status(
    gen_service: GenerationService = Depends(get_generation_service),
) -> GenerationStatusResponse:
    """Get the current generation status."""
    status = gen_service.get_status()
    return GenerationStatusResponse(
        state=status.state.value,
        request_id=status.request_id,
        started_at=status.started_at,
        completed_at=status.completed_at,
        error=status.error,
        recipe_count=status.recipe_count,
        warnings=status.warnings,
    )


@router.get("/debug/history-state")
def debug_history_state(
    gen_service: GenerationService = Depends(get_generation_service),
) -> dict:
    """Temporary debug endpoint — remove after diagnosing history issue."""
    from morsl.app.api.dependencies import _services, get_history_service, get_settings

    hs_from_gen = gen_service._history_service
    hs_from_di = _services.get("history")
    settings = get_settings()
    hs_from_factory = get_history_service(settings)

    # Simulate what the /api/history route does
    entries_from_di, total_from_di = hs_from_factory.list_entries(limit=5, offset=0)

    return {
        "gen_history_entries": len(hs_from_gen._entries) if hs_from_gen else -1,
        "di_history_entries": len(hs_from_di._entries) if hs_from_di else -1,
        "factory_history_entries": len(hs_from_factory._entries),
        "same_instance_gen_di": hs_from_gen is hs_from_di,
        "same_instance_gen_factory": hs_from_gen is hs_from_factory,
        "list_entries_total": total_from_di,
        "list_entries_count": len(entries_from_di),
        "first_entry_profile": entries_from_di[0].get("profile") if entries_from_di else None,
        "singleton_keys": list(_services.keys()),
    }


@router.patch("/menu/swap", response_model=RecipeResponse)
def swap_recipe(
    request: SwapRequest,
    gen_service: GenerationService = Depends(get_generation_service),
    config_service: ConfigService = Depends(get_config_service),
    credentials: tuple[str, str] = Depends(get_credentials),
    logger: Logger = Depends(get_logger),
) -> RecipeResponse:
    """Replace one recipe in the current menu without regenerating."""
    try:
        config = config_service.load_profile(request.profile)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404, detail=f"Profile '{request.profile}' not found"
        ) from e

    url, token = credentials
    try:
        new_recipe = gen_service.swap_recipe(
            old_recipe_id=request.old_recipe_id,
            config=config,
            url=url,
            token=token,
            logger=logger,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return RecipeResponse(**new_recipe)


@router.get("/menu/stream")
async def menu_stream(
    request: Request,
    gen_service: GenerationService = Depends(get_generation_service),
) -> StreamingResponse:
    """SSE stream for real-time menu change notifications.

    Events:
    - connected: includes app version for reload detection
    - generating: generation started
    - menu_updated: new menu available
    - menu_cleared: menu was deleted
    """
    queue = gen_service.subscribe()
    app_version = request.app.version

    async def event_generator():
        try:
            yield f"event: connected\ndata: {json.dumps({'version': app_version})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=SSE_QUEUE_TIMEOUT)
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            gen_service.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
