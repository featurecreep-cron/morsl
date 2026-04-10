from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from morsl.app.api.dependencies import get_generation_service, require_admin
from morsl.app.api.models import GenerationStatusResponse, MenuResponse
from morsl.constants import SSE_QUEUE_TIMEOUT
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
