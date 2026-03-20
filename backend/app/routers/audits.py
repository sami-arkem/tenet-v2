"""
Audits router — Bible §4.4.
Every endpoint: auth required, tenant isolation enforced at DB level.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.db.queries import (
    create_audit_run,
    get_audit_run,
    get_running_audit,
    list_audit_runs,
    write_audit_log,
)
from app.schemas.audit import AuditListResponse, AuditRunResponse, CreateAuditRequest
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[AuditRunResponse],
    status_code=201,
    summary="Start a new audit run",
)
async def create_audit(
    request: Request,
    body: CreateAuditRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditRunResponse]:
    """
    Bible §4.4: validates no audit running, creates audit record, queues async execution.
    Returns 409 if audit already PENDING/RUNNING for this entity.
    """
    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    # Check no audit already running
    if not body.force:
        existing = await get_running_audit(
            db, tenant_id=tenant_id, entity_id=str(body.entity_id) if body.entity_id else None
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "AUDIT_IN_PROGRESS",
                    "message": f"An audit is already running (run_id: {existing['id']})",
                },
            )

    run = await create_audit_run(
        db,
        tenant_id=tenant_id,
        entity_id=str(body.entity_id) if body.entity_id else None,
        jurisdiction=body.jurisdiction,
        regime_scope=body.regime_scope,
        company_profile=body.company_profile,
        evidence_ids=[str(e) for e in body.evidence_ids],
        started_by=user_id,
    )

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="AUDIT_STARTED",
        resource_type="audit_run",
        resource_id=run["id"],
        request_id=getattr(request.state, "request_id", None),
    )

    return ApiResponse.success(
        data=_to_response(run),
        request_id=getattr(request.state, "request_id", None),
        run_id=run["id"],
    )


@router.get(
    "",
    response_model=ApiResponse[AuditListResponse],
    summary="List audit runs for this tenant",
)
async def list_audits(
    request: Request,
    entity_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditListResponse]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    if limit > 100:
        limit = 100

    result = await list_audit_runs(
        db,
        tenant_id=tenant_id,
        entity_id=entity_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return ApiResponse.success(
        data=AuditListResponse(
            items=[_to_response(r) for r in result["items"]],
            total=result["total"],
            limit=limit,
            offset=offset,
        ),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{run_id}",
    response_model=ApiResponse[AuditRunResponse],
    summary="Get audit run detail",
)
async def get_audit(
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditRunResponse]:
    """Returns 404 if run_id belongs to a different tenant (tenant isolation)."""
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=run_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    return ApiResponse.success(
        data=_to_response(run),
        request_id=getattr(request.state, "request_id", None),
        run_id=run_id,
    )


def _to_response(row: dict) -> AuditRunResponse:
    return AuditRunResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        entity_id=str(row["entity_id"]) if row.get("entity_id") else None,
        status=row["status"],
        jurisdiction=row["jurisdiction"],
        regime_scope=list(row.get("regime_scope") or []),
        overall_verdict=row.get("overall_verdict"),
        posture=row.get("posture"),
        control_count=row.get("control_count") or 0,
        pass_count=row.get("pass_count") or 0,
        partial_count=row.get("partial_count") or 0,
        fail_count=row.get("fail_count") or 0,
        missing_count=row.get("missing_count") or 0,
        na_count=row.get("na_count") or 0,
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
        duration_seconds=row.get("duration_seconds"),
        gold_case_version=row.get("gold_case_version"),
        model_version=row.get("model_version") or "claude-sonnet-4-6",
    )
