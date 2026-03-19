from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from api.schemas import Envelope, MetaBody
from api.store import new_request_id, utc_now_iso
from core.audit_planner import (
    build_audit_plan_from_pack,
    build_audit_plan_from_scope,
    build_execution_payload_from_pack,
)


class ScopePlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_profile: dict[str, Any]
    scope: dict[str, Any]


class AuditPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = None
    audit_type: str | None = None
    domains: list[str]
    jurisdictions: list[str]
    framework_ids: list[str]
    selected_control_count: int
    excluded_control_count: int
    selected_controls: list[dict[str, Any]]
    excluded_controls: list[dict[str, Any]]
    pack_id: str | None = None
    pack_name: str | None = None


class PackExecutionPayloadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]


router = APIRouter(prefix="/v1/planning", tags=["planning"])


def build_meta() -> MetaBody:
    return MetaBody(
        request_id=new_request_id(),
        timestamp=utc_now_iso(),
        version="1.0",
    )


@router.post("/scope", response_model=Envelope[AuditPlanResponse])
def planning_from_scope(request: ScopePlanningRequest) -> Envelope[AuditPlanResponse]:
    try:
        plan = build_audit_plan_from_scope(
            company_profile=request.company_profile,
            scope=request.scope,
        )
        return Envelope[AuditPlanResponse](
            data=AuditPlanResponse(**plan),
            meta=build_meta(),
            error=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"audit planning failed: {exc}") from exc


@router.get("/evidence-packs/{pack_id}", response_model=Envelope[AuditPlanResponse])
def planning_from_pack(pack_id: str) -> Envelope[AuditPlanResponse]:
    try:
        plan = build_audit_plan_from_pack(pack_id)
        return Envelope[AuditPlanResponse](
            data=AuditPlanResponse(**plan),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pack planning failed: {exc}") from exc


@router.get("/evidence-packs/{pack_id}/execution-payload", response_model=Envelope[PackExecutionPayloadResponse])
def planning_execution_payload(pack_id: str) -> Envelope[PackExecutionPayloadResponse]:
    try:
        payload = build_execution_payload_from_pack(pack_id)
        return Envelope[PackExecutionPayloadResponse](
            data=PackExecutionPayloadResponse(payload=payload),
            meta=build_meta(),
            error=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"execution payload planning failed: {exc}") from exc
