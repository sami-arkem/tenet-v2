from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.audit_preparation import OCRSubmissionRequest
from apps.api.schemas.response import ApiResponse
from core.evidence_application_service import EvidenceApplicationPaths
from core.model_call_logger import ModelLogPaths
from core.ocr_submission_service import OCRSubmissionPaths, submit_ocr_text


router = APIRouter()


def _ocr_paths() -> OCRSubmissionPaths:
    return OCRSubmissionPaths(os.getenv("TENET_STATE_DIR", "state"))


def _evidence_paths() -> EvidenceApplicationPaths:
    return EvidenceApplicationPaths(os.getenv("TENET_STATE_DIR", "state"))


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


@router.post("/{evidence_id}")
async def submit_ocr_endpoint(evidence_id: str, body: OCRSubmissionRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = submit_ocr_text(
            paths=_ocr_paths(),
            evidence_paths=_evidence_paths(),
            model_log_paths=_model_log_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
            ocr_text=body.ocr_text,
        )
        return _api_success(request, result)
    except Exception as exc:
        raise _translate_error(request, exc)
