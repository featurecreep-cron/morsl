from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from morsl.app.api.dependencies import get_order_service, get_settings_service, require_admin
from morsl.app.api.models import OrderRequest, OrderStatusUpdate
from morsl.constants import SSE_QUEUE_TIMEOUT
from morsl.services.order_service import OrderService
from morsl.services.settings_service import SettingsService
from morsl.utils import now

router = APIRouter(tags=["orders"])


@router.post("/orders")
def place_order(
    body: OrderRequest,
    order_service: OrderService = Depends(get_order_service),
    settings_svc: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Place an order. Creates a Tandoor meal plan entry with configured meal type."""
    app_settings = settings_svc.get_all()
    if not app_settings.get("orders_enabled", True):
        raise HTTPException(status_code=403, detail="Orders are currently disabled")

    servings = body.servings or 1

    if not app_settings.get("save_orders_to_tandoor", True):
        timestamp = now()
        order = {
            "id": f"local-{int(timestamp.timestamp())}",
            "recipe_id": body.recipe_id,
            "recipe_name": body.recipe_name,
            "timestamp": timestamp.isoformat(),
            "servings": servings,
            "meal_plan_id": None,
            "customer_name": body.customer_name,
        }
        order_service.store_and_notify(order)
        return order

    meal_type_id = app_settings.get("order_meal_type_id")
    order = order_service.place_order(
        recipe_id=body.recipe_id,
        recipe_name=body.recipe_name,
        servings=servings,
        customer_name=body.customer_name,
        meal_type_id=meal_type_id,
    )
    return order


@router.get("/orders", dependencies=[Depends(require_admin)])
def get_orders(
    order_service: OrderService = Depends(get_order_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> List[Dict[str, Any]]:
    """Get all orders for date range (defaults to today), newest first."""
    fd = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
    td = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
    meal_type_id = settings_svc.get_all().get("order_meal_type_id")
    return order_service.get_orders(from_date=fd, to_date=td, meal_type_id=meal_type_id)


@router.get("/orders/counts", dependencies=[Depends(require_admin)])
def get_order_counts(
    order_service: OrderService = Depends(get_order_service),
    settings_svc: SettingsService = Depends(get_settings_service),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Per-recipe order counts for date range (defaults to today)."""
    fd = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
    td = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
    meal_type_id = settings_svc.get_all().get("order_meal_type_id")
    return {
        "counts": list(
            order_service.get_order_counts(
                from_date=fd, to_date=td, meal_type_id=meal_type_id
            ).values()
        )
    }


@router.delete("/orders/{order_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service),
) -> None:
    """Delete a single order."""
    try:
        order_service.delete_order(order_id)
    except RuntimeError:
        raise HTTPException(status_code=404, detail="Order not found") from None


@router.delete("/orders", status_code=200, dependencies=[Depends(require_admin)])
def clear_orders(
    order_service: OrderService = Depends(get_order_service),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """Clear all orders for date range (defaults to today). Returns count deleted."""
    fd = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
    td = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
    count = order_service.clear_orders(from_date=fd, to_date=td)
    return {"deleted": count}


@router.patch("/orders/{order_id}/status", dependencies=[Depends(require_admin)])
def update_order_status(
    order_id: str,
    body: OrderStatusUpdate,
    order_service: OrderService = Depends(get_order_service),
) -> Dict[str, Any]:
    """Update order status (e.g., mark as ready)."""
    order_service.update_status(order_id, body.status)
    return {"order_id": order_id, "status": body.status}


@router.get("/orders/customer-stream")
async def customer_order_stream(
    order_service: OrderService = Depends(get_order_service),
) -> StreamingResponse:
    """SSE stream for customer-facing order status updates (no auth required)."""
    queue = order_service.subscribe_customer()

    async def event_generator():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=SSE_QUEUE_TIMEOUT)
                    yield f"event: status_update\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            order_service.unsubscribe_customer(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/orders/stream", dependencies=[Depends(require_admin)])
async def order_stream(
    order_service: OrderService = Depends(get_order_service),
) -> StreamingResponse:
    """SSE stream for real-time order notifications."""
    queue = order_service.subscribe()

    async def event_generator():
        try:
            # Send initial keepalive
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    order = await asyncio.wait_for(queue.get(), timeout=SSE_QUEUE_TIMEOUT)
                    yield f"event: order\ndata: {json.dumps(order)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            order_service.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
