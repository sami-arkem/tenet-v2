from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.response import ApiResponse
from core.audit_preparation_service import AuditPreparationPaths, build_audit_preparation_summary, ensure_audit_requirements
from core.model_call_logger import ModelLogPaths, list_model_calls


router = APIRouter()


def _prep_paths() -> AuditPreparationPaths:
    return AuditPreparationPaths(os.getenv("TENET_STATE_DIR", "state"))


def _model_log_paths() -> ModelLogPaths:
    return ModelLogPaths(os.getenv("TENET_STATE_DIR", "state"))


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


@router.post("/{audit_id}/requirements/ensure")
async def ensure_requirements_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = ensure_audit_requirements(
            paths=_prep_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, {"audit_id": audit_id, "requirements": result})
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{audit_id}")
async def audit_preparation_summary_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = build_audit_preparation_summary(
            paths=_prep_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{audit_id}/model-calls")
async def audit_preparation_model_calls_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = list_model_calls(
            paths=_model_log_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)
