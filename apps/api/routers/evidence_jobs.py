from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.response import ApiResponse
from core.evidence_application_service import EvidenceApplicationPaths
from core.evidence_job_service import EvidenceJobPaths, list_jobs, run_next_job


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
                code="VALIDATION_ERROR",
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


def _job_paths() -> EvidenceJobPaths:
    return EvidenceJobPaths(os.getenv("TENET_STATE_DIR", "state"))


def _evidence_paths() -> EvidenceApplicationPaths:
    return EvidenceApplicationPaths(os.getenv("TENET_STATE_DIR", "state"))


@router.get("")
async def list_evidence_jobs_endpoint(request: Request, status: Optional[str] = None, _: None = Depends(require_authenticated_user)):
    try:
        result = list_jobs(
            paths=_job_paths(),
            tenant_id=request.state.tenant_id,
            status=status,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/run-next")
async def run_next_evidence_job_endpoint(request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = run_next_job(
            job_paths=_job_paths(),
            evidence_paths=_evidence_paths(),
            tenant_id=request.state.tenant_id,
            actor_user_id=request.state.user_id,
        )
        if result is None:
            return _api_success(request, {"status": "NO_JOBS_QUEUED"})
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)
