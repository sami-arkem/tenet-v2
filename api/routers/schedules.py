from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.schedule_service import (
    build_due_schedule_run_plan,
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    mark_schedule_run_executed,
    update_schedule,
)


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    name: str
    frequency: str
    starts_at: str
    timezone: str
    audit_payload: dict
    weekdays: list[str] | None = None
    day_of_month: int | None = None


class ScheduleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    frequency: str | None = None
    starts_at: str | None = None
    timezone: str | None = None
    audit_payload: dict | None = None
    weekdays: list[str] | None = None
    day_of_month: int | None = None
    status: str | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    tenant_id: str
    name: str
    frequency: str
    starts_at: str
    timezone: str
    audit_payload: dict
    status: str
    weekdays: list[str]
    day_of_month: int | None = None
    next_run_at: str | None = None
    last_run_at: str | None = None
    created_at: str
    updated_at: str
    deterministic_authoritative: bool


class ScheduleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


class ScheduleRunPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    candidate_count: int
    scheduled_count: int
    items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/schedules", tags=["schedules"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[ScheduleListResponse])
def schedules_list() -> Envelope[ScheduleListResponse]:
    try:
        payload = list_schedules()
        return Envelope[ScheduleListResponse](
            data=ScheduleListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule list failed: {exc}") from exc


@router.get("/planner/due", response_model=Envelope[ScheduleRunPlanResponse])
def schedules_due(limit: int = Query(default=50)) -> Envelope[ScheduleRunPlanResponse]:
    try:
        payload = build_due_schedule_run_plan(limit=limit)
        return Envelope[ScheduleRunPlanResponse](
            data=ScheduleRunPlanResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule planner failed: {exc}") from exc


@router.post("", response_model=Envelope[ScheduleResponse])
def schedules_create(request: ScheduleCreateRequest) -> Envelope[ScheduleResponse]:
    try:
        payload = create_schedule(
            tenant_id=request.tenant_id,
            name=request.name,
            frequency=request.frequency,
            starts_at=request.starts_at,
            timezone=request.timezone,
            audit_payload=request.audit_payload,
            weekdays=request.weekdays,
            day_of_month=request.day_of_month,
        )
        return Envelope[ScheduleResponse](
            data=ScheduleResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule create failed: {exc}") from exc


@router.get("/{schedule_id}", response_model=Envelope[ScheduleResponse])
def schedules_get(schedule_id: str) -> Envelope[ScheduleResponse]:
    try:
        payload = get_schedule(schedule_id=schedule_id)
        return Envelope[ScheduleResponse](
            data=ScheduleResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule get failed: {exc}") from exc


@router.patch("/{schedule_id}", response_model=Envelope[ScheduleResponse])
def schedules_update(schedule_id: str, request: ScheduleUpdateRequest) -> Envelope[ScheduleResponse]:
    try:
        payload = update_schedule(
            schedule_id=schedule_id,
            name=request.name,
            frequency=request.frequency,
            starts_at=request.starts_at,
            timezone=request.timezone,
            audit_payload=request.audit_payload,
            weekdays=request.weekdays,
            day_of_month=request.day_of_month,
            status=request.status,
        )
        return Envelope[ScheduleResponse](
            data=ScheduleResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule update failed: {exc}") from exc


@router.delete("/{schedule_id}", response_model=Envelope[dict])
def schedules_delete(schedule_id: str) -> Envelope[dict]:
    try:
        payload = delete_schedule(schedule_id=schedule_id)
        return Envelope[dict](data=payload, meta=build_meta(), error=None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule delete failed: {exc}") from exc


@router.post("/{schedule_id}/mark-executed", response_model=Envelope[ScheduleResponse])
def schedules_mark_executed(schedule_id: str) -> Envelope[ScheduleResponse]:
    try:
        payload = mark_schedule_run_executed(schedule_id=schedule_id)
        return Envelope[ScheduleResponse](
            data=ScheduleResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule mark executed failed: {exc}") from exc
