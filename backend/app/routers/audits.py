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
from app.schemas.audit import AuditListResponse, AuditSummaryResponse, CreateAuditRequest
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[AuditSummaryResponse],
    status_code=201,
    summary="Start a new audit run",
)
async def create_audit(
    request: Request,
    body: CreateAuditRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditSummaryResponse]:
    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    # Check no audit already running
    if not body.force:
        existing = await get_running_audit(
            db, tenant_id=tenant_id, entity_id=body.entity_id
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
        entity_id=body.entity_id,
        system_name=body.system_name,
        audit_kind=body.audit_kind,
        framework=body.framework,
        jurisdiction=body.jurisdiction,
        regime_scope=body.regime_scope or [body.framework],
        company_profile=body.company_profile,
        evidence_ids=body.evidence_ids,
        started_by=user_id,
        note=body.note,
    )

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="AUDIT_STARTED",
        resource_type="audit_run",
        resource_id=str(run["id"]),
        request_id=getattr(request.state, "request_id", None),
    )

    return ApiResponse.success(
        data=_to_response(run),
        request_id=getattr(request.state, "request_id", None),
        run_id=str(run["id"]),
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
    response_model=ApiResponse[AuditSummaryResponse],
    summary="Get audit run detail",
)
async def get_audit(
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditSummaryResponse]:
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


@router.get(
    "/{audit_id}/runs/latest",
    summary="Get latest run for an audit",
)
async def get_latest_run(
    audit_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    # In our model, the audit IS the run — return it as a run summary
    run = await get_audit_run(db, run_id=audit_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    return ApiResponse.success(
        data={
            "run_id": str(run["id"]),
            "audit_id": str(run["id"]),
            "tenant_id": str(run["tenant_id"]),
            "status": (run.get("status") or "CREATED").upper(),
            "deployment_decision": run.get("deployment_decision") or "UNKNOWN",
            "report_ready": False,
            "export_ready": False,
            "finalization_ready": False,
            "started_at": run.get("started_at"),
            "completed_at": run.get("completed_at"),
        },
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")


@router.post(
    "/{audit_id}/run",
    summary="Trigger an audit run",
)
async def trigger_audit_run(
    audit_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.db.queries import update_audit_run_status

    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    run = await get_audit_run(db, run_id=audit_id, tenant_id=tenant_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "AUDIT_NOT_FOUND", "message": "Audit run not found"},
        )

    current_status = (run.get("status") or "").upper()
    if current_status == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail={"code": "AUDIT_IN_PROGRESS", "message": "Audit is already running"},
        )

    # Update status to RUNNING
    await update_audit_run_status(
        db, run_id=audit_id, tenant_id=tenant_id, status="RUNNING"
    )
    await db.commit()

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="AUDIT_RUN_TRIGGERED",
        resource_type="audit_run",
        resource_id=audit_id,
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()

    return ApiResponse.success(
        data={
            "audit_id": audit_id,
            "run_id": audit_id,
            "queue_status": "started",
            "message": "Audit run triggered successfully",
        },
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")


def _to_response(row: dict) -> AuditSummaryResponse:
    """Map DB row to frontend AuditSummary shape."""
    status = (row.get("status") or "CREATED").upper()
    # Map internal statuses to frontend-expected values
    if status in ("PENDING",):
        status = "CREATED"
    if status in ("COMPLETE",):
        status = "COMPLETED"

    return AuditSummaryResponse(
        audit_id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        audit_kind=row.get("audit_kind") or "compliance_audit",
        entity_id=str(row["entity_id"]) if row.get("entity_id") else None,
        system_name=row.get("system_name") or "Untitled System",
        jurisdiction=row.get("jurisdiction") or "",
        framework=row.get("framework") or row.get("jurisdiction") or "",
        status=status,
        deployment_decision=row.get("deployment_decision") or "UNKNOWN",
        release_ready=bool(row.get("release_ready")),
        created_at=row.get("created_at") or row.get("started_at"),
        updated_at=row.get("updated_at") or row.get("created_at") or row.get("started_at"),
        overall_verdict=row.get("overall_verdict"),
        posture=row.get("posture"),
        control_count=row.get("control_count") or 0,
        pass_count=row.get("pass_count") or 0,
        partial_count=row.get("partial_count") or 0,
        fail_count=row.get("fail_count") or 0,
        missing_count=row.get("missing_count") or 0,
        na_count=row.get("na_count") or 0,
        latest_run_id=str(row["id"]),
        note=row.get("note"),
    )
