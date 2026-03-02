from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_scheduler_service, require_admin
from app.api.models import ScheduleRequest, ScheduleResponse
from services.scheduler_service import SchedulerService

router = APIRouter(tags=["schedules"], dependencies=[Depends(require_admin)])


@router.get("/schedules", response_model=List[ScheduleResponse])
def list_schedules(
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> List[ScheduleResponse]:
    """List all schedules."""
    return [ScheduleResponse(**s) for s in scheduler.list_schedules()]


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    body: ScheduleRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> ScheduleResponse:
    """Create a new schedule."""
    schedule = scheduler.create_schedule(body.model_dump())
    return ScheduleResponse(**schedule)


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: str,
    body: ScheduleRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> ScheduleResponse:
    """Update an existing schedule."""
    try:
        schedule = scheduler.update_schedule(schedule_id, body.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return ScheduleResponse(**schedule)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> None:
    """Delete a schedule."""
    try:
        scheduler.delete_schedule(schedule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
