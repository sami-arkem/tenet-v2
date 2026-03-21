from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from apps.api.deps.authz import require_authenticated_user, require_role
from apps.api.schemas.response import ApiResponse
from apps.api.utils import api_success as _api_success, now_iso
from core.remediation_dashboard import build_remediation_dashboard
from core.remediation_due_planner import (
    load_notification_outbox,
    plan_due_notifications,
    write_notification_outbox,
)
from core.remediation_lifecycle import load_lifecycle_items
from core.remediation_operator_service import (
    RemediationOperatorPaths,
    assign_owner_api,
    apply_verification_result_api,
    get_remediation_detail,
    list_remediations,
    set_due_date_api,
    transition_status_api,
)

router = APIRouter()


def _paths() -> RemediationOperatorPaths:
    base = os.getenv("TENET_STATE_DIR", "state")
    return RemediationOperatorPaths(
        items=f"{base}/remediation/remediation_items_operator.jsonl",
        timeline=f"{base}/remediation/remediation_timeline.jsonl",
        lifecycle_index=f"{base}/remediation/remediation_lifecycle_index.json",
        gate=f"{base}/remediation/remediation_gate.json",
        evidence_metadata=f"{base}/remediation/remediation_evidence_metadata.jsonl",
        notification_outbox=f"{base}/remediation/remediation_notification_outbox.jsonl",
        operator_audit_log=f"{base}/remediation/remediation_operator_audit_log.jsonl",
    )


def _actor_directory(request: Request) -> dict:
    actor_directory = getattr(request.state, "actor_directory", None)
    return actor_directory if isinstance(actor_directory, dict) else {}


def _translate_error(request: Request, exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(
            status_code=403,
            detail=ApiResponse.failure(
                code="INSUFFICIENT_PERMISSIONS",
                message=str(exc),
                request_id=request.state.request_id,
                timestamp=request.state.timestamp,
                run_id=getattr(request.state, "run_id", None),
            ).model_dump(),
        )
    if isinstance(exc, ValueError):
        msg = str(exc)
        code = "VALIDATION_ERROR"
        if "not found" in msg.lower():
            code = "FINDING_NOT_FOUND"
        elif "note" in msg.lower():
            code = "FINDING_NOTE_REQUIRED"
        elif "transition" in msg.lower():
            code = "FINDING_INVALID_STATUS"
        elif "evidence" in msg.lower():
            code = "FINDING_EVIDENCE_REQUIRED"
        return HTTPException(
            status_code=400,
            detail=ApiResponse.failure(
                code=code,
                message=msg,
                request_id=request.state.request_id,
                timestamp=request.state.timestamp,
                run_id=getattr(request.state, "run_id", None),
            ).model_dump(),
        )
    return HTTPException(
        status_code=500,
        detail=ApiResponse.failure(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            request_id=request.state.request_id,
            timestamp=request.state.timestamp,
            run_id=getattr(request.state, "run_id", None),
        ).model_dump(),
    )


class AssignOwnerRequest(BaseModel):
    owner_user_id: str = Field(min_length=1)
    note: str = Field(min_length=10)


class DueDateRequest(BaseModel):
    due_date: str = Field(min_length=10, max_length=10)
    note: str = Field(min_length=10)


class EvidenceFileInput(BaseModel):
    file_id: str
    filename: str
    content_type: str
    sha256: str
    byte_size: int


class StatusTransitionRequest(BaseModel):
    to_status: str
    note: str = Field(min_length=10)
    evidence_files: list[EvidenceFileInput] = Field(default_factory=list)


class VerificationResultRequest(BaseModel):
    verification_passed: bool
    updated_gap_note: Optional[str] = None


@router.get("")
async def list_remediation_endpoint(request: Request, _: None = Depends(require_authenticated_user)):
    try:
        rows = list_remediations(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            items_path=Path(_paths().items),
        )
        return _api_success(request, rows)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/dashboard")
async def remediation_dashboard_endpoint(
    request: Request,
    today: Optional[str] = None,
    _: None = Depends(require_authenticated_user),
):
    try:
        rows = list_remediations(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            items_path=Path(_paths().items),
        )
        dashboard = build_remediation_dashboard(
            lifecycle_items=rows,
            actor_user_id=request.state.user_id,
            tenant_id=request.state.tenant_id,
            today=today or datetime.now(timezone.utc).date().isoformat(),
        )
        return _api_success(request, dashboard.to_dict())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{remediation_id}")
async def remediation_detail_endpoint(
    remediation_id: str,
    request: Request,
    _: None = Depends(require_authenticated_user),
):
    try:
        detail = get_remediation_detail(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            remediation_id=remediation_id,
            items_path=Path(_paths().items),
            timeline_path=Path(_paths().timeline),
            evidence_metadata_path=Path(_paths().evidence_metadata),
        )
        return _api_success(request, detail)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{remediation_id}/assign-owner")
async def remediation_assign_owner_endpoint(
    remediation_id: str,
    body: AssignOwnerRequest,
    request: Request,
    _: None = Depends(require_role(["ADMIN", "OWNER"])),
):
    try:
        result = assign_owner_api(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            remediation_id=remediation_id,
            owner_user_id=body.owner_user_id,
            note=body.note,
            operator_paths=_paths(),
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{remediation_id}/due-date")
async def remediation_due_date_endpoint(
    remediation_id: str,
    body: DueDateRequest,
    request: Request,
    _: None = Depends(require_role(["ADMIN", "OWNER"])),
):
    try:
        result = set_due_date_api(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            remediation_id=remediation_id,
            due_date=body.due_date,
            note=body.note,
            operator_paths=_paths(),
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{remediation_id}/status")
async def remediation_status_endpoint(
    remediation_id: str,
    body: StatusTransitionRequest,
    request: Request,
    _: None = Depends(require_role(["ADMIN", "OWNER", "ANALYST"])),
):
    try:
        result = transition_status_api(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            remediation_id=remediation_id,
            to_status=body.to_status,
            note=body.note,
            operator_paths=_paths(),
            evidence_files=[item.model_dump() for item in body.evidence_files],
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{remediation_id}/verification-result")
async def remediation_verification_result_endpoint(
    remediation_id: str,
    body: VerificationResultRequest,
    request: Request,
    _: None = Depends(require_role(["ADMIN", "OWNER", "ANALYST"])),
):
    try:
        result = apply_verification_result_api(
            actor_directory=_actor_directory(request),
            actor_user_id=request.state.user_id,
            remediation_id=remediation_id,
            verification_passed=body.verification_passed,
            updated_gap_note=body.updated_gap_note,
            operator_paths=_paths(),
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/jobs/plan-due-notifications")
async def remediation_plan_due_notifications_endpoint(
    request: Request,
    today: Optional[str] = None,
    now: Optional[str] = None,
    _: None = Depends(require_role(["ADMIN", "OWNER"])),
):
    try:
        items = load_lifecycle_items(Path(_paths().items))
        scoped = [row for row in items if str(row["tenant_id"]) == request.state.tenant_id]
        existing = load_notification_outbox(Path(_paths().notification_outbox))
        scoped_existing = [row for row in existing if str(row["tenant_id"]) == request.state.tenant_id]
        other = [row for row in existing if str(row["tenant_id"]) != request.state.tenant_id]

        planned = plan_due_notifications(
            lifecycle_items=scoped,
            existing_outbox=scoped_existing,
            today=today or datetime.now(timezone.utc).date().isoformat(),
            now=now or now_iso(),
        )
        write_notification_outbox(Path(_paths().notification_outbox), other + planned)
        return _api_success(request, {"planned_events": len(planned) - len(scoped_existing)})
    except Exception as exc:
        raise _translate_error(request, exc)
