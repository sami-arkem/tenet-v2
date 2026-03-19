from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.response import ApiResponse
from core.audit_runtime_service import get_findings_list, runtime_paths


router = APIRouter()


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
        return HTTPException(
            status_code=400,
            detail=ApiResponse.failure(
                code="FINDING_NOT_FOUND" if "not found" in str(exc).lower() else "VALIDATION_ERROR",
                message=str(exc),
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
    return runtime_paths(os.getenv("TENET_STATE_DIR", "state"))


@router.get("/audit/{audit_id}")
async def findings_for_audit_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = get_findings_list(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)
