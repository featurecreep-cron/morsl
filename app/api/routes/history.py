from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_history_service, require_admin
from app.api.models import AnalyticsResponse, HistoryEntryResponse, HistoryListResponse
from services.history_service import HistoryService

router = APIRouter(tags=["history"], dependencies=[Depends(require_admin)])


# IMPORTANT: /history/analytics must come before /history/{entry_id}
@router.get("/history/analytics", response_model=AnalyticsResponse)
def get_analytics(
    svc: HistoryService = Depends(get_history_service),
) -> Dict[str, Any]:
    """Compute constraint analytics from generation history."""
    return svc.get_analytics()


@router.get("/history", response_model=HistoryListResponse)
def list_history(
    limit: int = 50,
    offset: int = 0,
    svc: HistoryService = Depends(get_history_service),
) -> Dict[str, Any]:
    """Return paginated generation history (newest first)."""
    entries, total = svc.list_entries(limit=min(limit, 100), offset=max(offset, 0))
    return {"entries": entries, "total": total}


@router.get("/history/{entry_id}", response_model=HistoryEntryResponse)
def get_history_entry(
    entry_id: str = Path(..., pattern=r"^[a-f0-9-]{36}$"),
    svc: HistoryService = Depends(get_history_service),
) -> Dict[str, Any]:
    """Get a single history entry by ID."""
    entry = svc.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    return entry


@router.delete("/history", status_code=204)
def clear_history(
    svc: HistoryService = Depends(get_history_service),
) -> None:
    """Delete all generation history."""
    svc.clear()
