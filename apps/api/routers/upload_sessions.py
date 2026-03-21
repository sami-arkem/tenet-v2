from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.response import ApiResponse
from apps.api.utils import api_success as _api_success
from apps.api.schemas.upload_sessions import (
    CancelUploadSessionRequest,
    CreateUploadSessionRequest,
    FailUploadSessionRequest,
    FinalizeUploadSessionRequest,
)
from core.blob_store import BlobStorePaths
from core.evidence_application_service import EvidenceApplicationPaths
from core.evidence_job_service import EvidenceJobPaths
from core.upload_session_service import (
    UploadSessionPaths,
    cancel_upload_session,
    create_upload_session,
    fail_upload_session,
    finalize_upload_session,
    list_upload_sessions,
)


router = APIRouter()


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
            code = "UPLOAD_SESSION_NOT_FOUND"
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


def _session_paths() -> UploadSessionPaths:
    return UploadSessionPaths(os.getenv("TENET_STATE_DIR", "state"))


def _blob_paths() -> BlobStorePaths:
    return BlobStorePaths(os.getenv("TENET_STATE_DIR", "state"))


def _evidence_paths() -> EvidenceApplicationPaths:
    return EvidenceApplicationPaths(os.getenv("TENET_STATE_DIR", "state"))


def _job_paths() -> EvidenceJobPaths:
    return EvidenceJobPaths(os.getenv("TENET_STATE_DIR", "state"))


@router.post("")
async def create_upload_session_endpoint(body: CreateUploadSessionRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = create_upload_session(
            paths=_session_paths(),
            tenant_id=request.state.tenant_id,
            actor_user_id=request.state.user_id,
            payload=body.model_dump(),
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("")
async def list_upload_sessions_endpoint(request: Request, audit_id: Optional[str] = None, _: None = Depends(require_authenticated_user)):
    try:
        result = list_upload_sessions(
            paths=_session_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{upload_session_id}/finalize")
async def finalize_upload_session_endpoint(upload_session_id: str, body: FinalizeUploadSessionRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = finalize_upload_session(
            session_paths=_session_paths(),
            blob_paths=_blob_paths(),
            evidence_paths=_evidence_paths(),
            job_paths=_job_paths(),
            tenant_id=request.state.tenant_id,
            actor_user_id=request.state.user_id,
            upload_session_id=upload_session_id,
            temp_file_path=body.temp_file_path,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{upload_session_id}/fail")
async def fail_upload_session_endpoint(upload_session_id: str, body: FailUploadSessionRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = fail_upload_session(
            paths=_session_paths(),
            tenant_id=request.state.tenant_id,
            upload_session_id=upload_session_id,
            error_message=body.error_message,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{upload_session_id}/cancel")
async def cancel_upload_session_endpoint(upload_session_id: str, body: CancelUploadSessionRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = cancel_upload_session(
            paths=_session_paths(),
            tenant_id=request.state.tenant_id,
            upload_session_id=upload_session_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)
