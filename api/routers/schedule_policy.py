from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.schedule_policy_service import (
    build_due_execution_plan,
    build_schedule_reminder_plan,
    create_policy_schedule,
    delete_policy_schedule,
    evaluate_schedule_auto_run_eligibility,
    get_policy_schedule,
    list_policy_schedules,
    mark_policy_schedule_executed,
    update_policy_schedule,
)


class SchedulePolicyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    created_by: str
    name: str
    regime_scope: list[str]
    jurisdiction: str
    frequency: str
    next_run_date: str
    audit_payload: dict
    entity_id: str | None = None
    notify_before_days: int = 7
    notify_users: list[str] = []
    custom_interval_days: int | None = None


class SchedulePolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    regime_scope: list[str] | None = None
    jurisdiction: str | None = None
    frequency: str | None = None
    next_run_date: str | None = None
    audit_payload: dict | None = None
    entity_id: str | None = None
    notify_before_days: int | None = None
    notify_users: list[str] | None = None
    custom_interval_days: int | None = None
    status: str | None = None
    is_active: bool | None = None


class SchedulePolicyMarkExecutedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_run_id: str
    executed_at: str


class SchedulePolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    tenant_id: str
    entity_id: str | None = None
    created_by: str
    name: str
    regime_scope: list[str]
    jurisdiction: str
    frequency: str
    custom_interval_days: int | None = None
    next_run_date: str
    last_run_id: str | None = None
    last_run_at: str | None = None
    notify_before_days: int
    notify_users: list[str]
    status: str
    is_active: bool
    audit_payload: dict
    created_at: str
    updated_at: str
    deterministic_authoritative: bool


class SchedulePolicyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    items: list[dict]
    deterministic_authoritative: bool


class ScheduleReminderPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: str
    count: int
    items: list[dict]
    deterministic_authoritative: bool


class ScheduleEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    eligible: bool
    skip_reasons: list[str]
    next_run_date: str
    as_of_date: str
    latest_evidence_at: str | None = None
    evidence_age_days: int | None = None
    deterministic_authoritative: bool


class ScheduleDueExecutionPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: str
    eligible_count: int
    scheduled_count: int
    eligible_items: list[dict]
    skipped_count: int
    skipped_items: list[dict]
    deterministic_authoritative: bool


router = APIRouter(prefix="/v1/schedule-policy", tags=["schedule-policy"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.get("", response_model=Envelope[SchedulePolicyListResponse])
def schedule_policy_list() -> Envelope[SchedulePolicyListResponse]:
    try:
        payload = list_policy_schedules()
        return Envelope[SchedulePolicyListResponse](
            data=SchedulePolicyListResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy list failed: {exc}") from exc


@router.get("/planner/reminders", response_model=Envelope[ScheduleReminderPlanResponse])
def schedule_policy_reminders() -> Envelope[ScheduleReminderPlanResponse]:
    try:
        payload = build_schedule_reminder_plan()
        return Envelope[ScheduleReminderPlanResponse](
            data=ScheduleReminderPlanResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule reminder planner failed: {exc}") from exc


@router.get("/planner/due", response_model=Envelope[ScheduleDueExecutionPlanResponse])
def schedule_policy_due(limit: int = Query(default=50)) -> Envelope[ScheduleDueExecutionPlanResponse]:
    try:
        payload = build_due_execution_plan(limit=limit)
        return Envelope[ScheduleDueExecutionPlanResponse](
            data=ScheduleDueExecutionPlanResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule due planner failed: {exc}") from exc


@router.post("", response_model=Envelope[SchedulePolicyResponse])
def schedule_policy_create(request: SchedulePolicyCreateRequest) -> Envelope[SchedulePolicyResponse]:
    try:
        payload = create_policy_schedule(
            tenant_id=request.tenant_id,
            created_by=request.created_by,
            name=request.name,
            regime_scope=request.regime_scope,
            jurisdiction=request.jurisdiction,
            frequency=request.frequency,
            next_run_date=request.next_run_date,
            audit_payload=request.audit_payload,
            entity_id=request.entity_id,
            notify_before_days=request.notify_before_days,
            notify_users=request.notify_users,
            custom_interval_days=request.custom_interval_days,
        )
        return Envelope[SchedulePolicyResponse](
            data=SchedulePolicyResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy create failed: {exc}") from exc


@router.get("/{schedule_id}", response_model=Envelope[SchedulePolicyResponse])
def schedule_policy_get(schedule_id: str) -> Envelope[SchedulePolicyResponse]:
    try:
        payload = get_policy_schedule(schedule_id=schedule_id)
        return Envelope[SchedulePolicyResponse](
            data=SchedulePolicyResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy get failed: {exc}") from exc


@router.get("/{schedule_id}/eligibility", response_model=Envelope[ScheduleEligibilityResponse])
def schedule_policy_eligibility(schedule_id: str) -> Envelope[ScheduleEligibilityResponse]:
    try:
        schedule = get_policy_schedule(schedule_id=schedule_id)
        payload = evaluate_schedule_auto_run_eligibility(schedule=schedule)
        return Envelope[ScheduleEligibilityResponse](
            data=ScheduleEligibilityResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy eligibility failed: {exc}") from exc


@router.patch("/{schedule_id}", response_model=Envelope[SchedulePolicyResponse])
def schedule_policy_update(schedule_id: str, request: SchedulePolicyUpdateRequest) -> Envelope[SchedulePolicyResponse]:
    try:
        payload = update_policy_schedule(schedule_id=schedule_id, **request.model_dump(exclude_none=True))
        return Envelope[SchedulePolicyResponse](
            data=SchedulePolicyResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy update failed: {exc}") from exc


@router.delete("/{schedule_id}", response_model=Envelope[dict])
def schedule_policy_delete(schedule_id: str) -> Envelope[dict]:
    try:
        payload = delete_policy_schedule(schedule_id=schedule_id)
        return Envelope[dict](data=payload, meta=build_meta(), error=None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule policy delete failed: {exc}") from exc


@router.post("/{schedule_id}/mark-executed", response_model=Envelope[SchedulePolicyResponse])
def schedule_policy_mark_executed(
    schedule_id: str,
    request: SchedulePolicyMarkExecutedRequest,
) -> Envelope[SchedulePolicyResponse]:
    try:
        payload = mark_policy_schedule_executed(
            schedule_id=schedule_id,
            last_run_id=request.last_run_id,
            executed_at=request.executed_at,
        )
        return Envelope[SchedulePolicyResponse](
            data=SchedulePolicyResponse(**payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"schedule mark executed failed: {exc}") from exc
