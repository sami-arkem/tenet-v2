from __future__ import annotations

import os
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.api.deps.authz import require_authenticated_user
from apps.api.schemas.evidence import (
    CancelEvidenceUploadRequest,
    CompleteEvidenceUploadRequest,
    FailEvidenceUploadRequest,
    MarkEvidenceReadyRequest,
    RegisterEvidenceUploadRequest,
)
from apps.api.schemas.response import ApiResponse
from core.evidence_application_service import (
    EvidenceApplicationPaths,
    cancel_upload,
    complete_upload,
    fail_upload,
    get_evidence_detail,
    list_evidence,
    mark_ready,
    recompute_audit_evidence_gate,
    register_upload,
    seed_audit_requirements,
)


router = APIRouter()


def _paths() -> EvidenceApplicationPaths:
    return EvidenceApplicationPaths(os.getenv("TENET_STATE_DIR", "state"))


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
        if "DUPLICATE" in msg:
            code = "EVIDENCE_DUPLICATE"
        elif "IMMUTABLE" in msg:
            code = "EVIDENCE_IMMUTABLE"
        elif "not found" in msg.lower():
            code = "EVIDENCE_NOT_FOUND"
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


@router.post("/register")
async def register_evidence_endpoint(body: RegisterEvidenceUploadRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = register_upload(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            actor_user_id=request.state.user_id,
            payload=body.model_dump(),
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{evidence_id}/complete")
async def complete_evidence_endpoint(evidence_id: str, body: CompleteEvidenceUploadRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = complete_upload(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
            storage_path=body.storage_path,
            processing_started=body.processing_started,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{evidence_id}/fail")
async def fail_evidence_endpoint(evidence_id: str, body: FailEvidenceUploadRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = fail_upload(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
            error_message=body.error_message,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{evidence_id}/cancel")
async def cancel_evidence_endpoint(evidence_id: str, body: CancelEvidenceUploadRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = cancel_upload(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/{evidence_id}/mark-ready")
async def mark_ready_endpoint(evidence_id: str, body: MarkEvidenceReadyRequest, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = mark_ready(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
            extracted_text_ready=body.extracted_text_ready,
            inventory_ready=body.inventory_ready,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("")
async def list_evidence_endpoint(request: Request, audit_id: Optional[str] = None, _: None = Depends(require_authenticated_user)):
    try:
        result = list_evidence(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.get("/{evidence_id}")
async def evidence_detail_endpoint(evidence_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = get_evidence_detail(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            evidence_id=evidence_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/audits/{audit_id}/requirements/seed")
async def seed_requirements_endpoint(audit_id: str, request: Request, required_categories: List[str] = Query(default=None), _: None = Depends(require_authenticated_user)):
    try:
        if required_categories is None:
            required_categories = []
        seed_audit_requirements(
            paths=_paths(),
            audit_id=audit_id,
            required_categories=required_categories,
        )
        return _api_success(request, {"audit_id": audit_id, "required_categories": required_categories})
    except Exception as exc:
        raise _translate_error(request, exc)


@router.post("/audits/{audit_id}/gate/recompute")
async def recompute_gate_endpoint(audit_id: str, request: Request, _: None = Depends(require_authenticated_user)):
    try:
        result = recompute_audit_evidence_gate(
            paths=_paths(),
            tenant_id=request.state.tenant_id,
            audit_id=audit_id,
        )
        return _api_success(request, result.model_dump())
    except Exception as exc:
        raise _translate_error(request, exc)
