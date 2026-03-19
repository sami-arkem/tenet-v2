from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.audits import CreateAuditRequest
from apps.api.schemas.response import ApiResponse
from core.audit_runtime_service import execute_audit_run, runtime_paths
from core.audit_application_service import (
    create_audit,
    default_paths,
    get_audit_detail,
    get_release_summary,
    get_run_summary,
    list_audits,
    sync_audit_run_from_artifacts,
    trigger_audit_run,
    upsert_findings_from_reason_output,
)


router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _api_success(request: Request, data: Any) -> dict:
    return ApiResponse.success(
        data=data,
        request_id=request.state.request_id,
        timestamp=request.state.timestamp,
        run_id=getattr(request.state, "run_id", None),
    ).model_dump()


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
            code = "AUDIT_NOT_FOUND"
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


def _paths():
    base = os.getenv("TENET_STATE_DIR", "state")
    return default_paths(base)


@router.get("")
async def list_audits_endpoint(request: Request, _: None = Depends(require_authenticated_user)):
    try:
        rows = list_audits(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
        )
        return _api_success(request, [row.model_dump() for row in rows])
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("")
async def create_audit_endpoint(body: CreateAuditRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = create_audit(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            actor_user_id=request.state.user_id,
            payload=body.model_dump(),
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{audit_id}")
async def audit_detail_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = get_audit_detail(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{audit_id}/run")
async def trigger_audit_run_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = execute_audit_run(
            paths=runtime_paths(os.getenv("TENET_STATE_DIR", "state")),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{audit_id}/runs/sync")
async def sync_audit_run_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = sync_audit_run_from_artifacts(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{audit_id}/runs/latest")
async def get_latest_run_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = get_run_summary(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{audit_id}/findings/sync")
async def sync_findings_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = upsert_findings_from_reason_output(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{audit_id}/release")
async def get_release_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        row = get_release_summary(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, row.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)
