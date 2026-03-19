from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.remediation_dashboard import build_remediation_dashboard
from core.remediation_operator_service import (
    RemediationOperatorPaths,
    assign_owner_api,
    apply_verification_result_api,
    get_remediation_detail,
    list_remediations,
    load_actor_directory,
    set_due_date_api,
    transition_status_api,
)
from core.remediation_lifecycle import load_lifecycle_items
from core.remediation_due_planner import (
    load_notification_outbox,
    plan_due_notifications,
    write_notification_outbox,
)

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _request_id() -> str:
    return str(uuid.uuid4())


def _success(data: Any) -> Dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "request_id": _request_id(),
            "timestamp": _now_iso(),
            "version": "1.0",
        },
        "error": None,
    }


def _failure(code: str, message: str, details: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "data": None,
        "meta": {
            "request_id": _request_id(),
            "timestamp": _now_iso(),
            "version": "1.0",
        },
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


def _operator_paths() -> RemediationOperatorPaths:
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


def _actor_directory(request: Request) -> Dict[str, Dict[str, object]]:
    provider = getattr(request.app.state, "actor_directory_provider", None)
    if callable(provider):
        data = provider()
        if isinstance(data, dict):
            return data
    static_directory = getattr(request.app.state, "actor_directory", None)
    if isinstance(static_directory, dict):
        return static_directory

    actor_dir_path = os.getenv("TENET_ACTOR_DIRECTORY_PATH")
    if actor_dir_path:
        return load_actor_directory(Path(actor_dir_path))

    current_user_id = getattr(request.state, "user_id", None)
    current_tenant_id = getattr(request.state, "tenant_id", None)
    current_role = getattr(request.state, "user_role", None)
    if current_user_id and current_tenant_id and current_role:
        return {
            str(current_user_id): {
                "tenant_id": str(current_tenant_id),
                "role": str(current_role).upper(),
            }
        }
    return {}


def _current_actor_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail=_failure("UNAUTHORIZED", "Authentication required"))
    return str(user_id)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=_failure("INSUFFICIENT_PERMISSIONS", str(exc)))
    if isinstance(exc, ValueError):
        message = str(exc)
        code = "VALIDATION_ERROR"
        if "not found" in message.lower():
            code = "FINDING_NOT_FOUND"
        elif "note" in message.lower():
            code = "FINDING_NOTE_REQUIRED"
        elif "transition" in message.lower():
            code = "FINDING_INVALID_STATUS"
        return HTTPException(status_code=400, detail=_failure(code, message))
    return HTTPException(status_code=500, detail=_failure("INTERNAL_ERROR", "An internal error occurred"))


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
async def list_remediation(request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        rows = list_remediations(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            items_path=Path(paths.items),
        )
        return _success(rows)
    except Exception as exc:
        raise _translate_error(exc)


@router.get("/dashboard")
async def remediation_dashboard(request: Request, today: Optional[str] = None):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        rows = list_remediations(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            items_path=Path(paths.items),
        )
        actor = actors[actor_user_id]
        dashboard = build_remediation_dashboard(
            lifecycle_items=rows,
            actor_user_id=actor_user_id,
            tenant_id=str(actor["tenant_id"]),
            today=today or datetime.now(timezone.utc).date().isoformat(),
        )
        return _success(dashboard.to_dict())
    except Exception as exc:
        raise _translate_error(exc)


@router.get("/{remediation_id}")
async def remediation_detail(remediation_id: str, request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        detail = get_remediation_detail(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            remediation_id=remediation_id,
            items_path=Path(paths.items),
            timeline_path=Path(paths.timeline),
            evidence_metadata_path=Path(paths.evidence_metadata),
        )
        return _success(detail)
    except Exception as exc:
        raise _translate_error(exc)


@router.post("/{remediation_id}/assign-owner")
async def remediation_assign_owner(remediation_id: str, body: AssignOwnerRequest, request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        result = assign_owner_api(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            remediation_id=remediation_id,
            owner_user_id=body.owner_user_id,
            note=body.note,
            operator_paths=paths,
        )
        return _success(result)
    except Exception as exc:
        raise _translate_error(exc)


@router.post("/{remediation_id}/due-date")
async def remediation_set_due_date(remediation_id: str, body: DueDateRequest, request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        result = set_due_date_api(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            remediation_id=remediation_id,
            due_date=body.due_date,
            note=body.note,
            operator_paths=paths,
        )
        return _success(result)
    except Exception as exc:
        raise _translate_error(exc)


@router.post("/{remediation_id}/status")
async def remediation_transition(remediation_id: str, body: StatusTransitionRequest, request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        result = transition_status_api(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            remediation_id=remediation_id,
            to_status=body.to_status,
            note=body.note,
            operator_paths=paths,
            evidence_files=[item.model_dump() for item in body.evidence_files],
        )
        return _success(result)
    except Exception as exc:
        raise _translate_error(exc)


@router.post("/{remediation_id}/verification-result")
async def remediation_verification_result(remediation_id: str, body: VerificationResultRequest, request: Request):
    actors = _actor_directory(request)
    actor_user_id = _current_actor_user_id(request)
    paths = _operator_paths()

    try:
        result = apply_verification_result_api(
            actor_directory=actors,
            actor_user_id=actor_user_id,
            remediation_id=remediation_id,
            verification_passed=body.verification_passed,
            updated_gap_note=body.updated_gap_note,
            operator_paths=paths,
        )
        return _success(result)
    except Exception as exc:
        raise _translate_error(exc)


@router.post("/jobs/plan-due-notifications")
async def remediation_plan_due_notifications(request: Request, today: Optional[str] = None, now: Optional[str] = None):
    actor_user_id = _current_actor_user_id(request)
    actors = _actor_directory(request)
    actor = actors.get(actor_user_id)
    if actor is None or str(actor.get("role", "")).upper() not in {"ADMIN", "OWNER"}:
        raise HTTPException(status_code=403, detail=_failure("INSUFFICIENT_PERMISSIONS", "Forbidden"))

    paths = _operator_paths()

    try:
        items = load_lifecycle_items(Path(paths.items))
        tenant_scoped_items = [row for row in items if str(row["tenant_id"]) == str(actor["tenant_id"])]
        outbox = load_notification_outbox(Path(paths.notification_outbox))
        scoped_existing = [row for row in outbox if str(row["tenant_id"]) == str(actor["tenant_id"])]
        unscoped_existing = [row for row in outbox if str(row["tenant_id"]) != str(actor["tenant_id"])]

        planned = plan_due_notifications(
            lifecycle_items=tenant_scoped_items,
            existing_outbox=scoped_existing,
            today=today or datetime.now(timezone.utc).date().isoformat(),
            now=now or _now_iso(),
        )
        write_notification_outbox(Path(paths.notification_outbox), unscoped_existing + planned)
        return _success({"planned_events": len(planned) - len(scoped_existing)})
    except Exception as exc:
        raise _translate_error(exc)
