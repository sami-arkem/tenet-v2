"""
Findings router — Bible §T.2.6.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.db.queries import get_finding, list_findings, update_finding, write_audit_log
from app.schemas.finding import (
    FindingActivityResponse,
    FindingListResponse,
    FindingResponse,
    UpdateFindingRequest,
)
from app.schemas.response import ApiResponse
from sqlalchemy import text

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[FindingListResponse],
    summary="List findings with filters",
)
async def list_findings_endpoint(
    request: Request,
    audit_run_id: str | None = None,
    verdict: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    regime: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FindingListResponse]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    result = await list_findings(
        db,
        tenant_id=tenant_id,
        audit_run_id=audit_run_id,
        verdict=verdict,
        severity=severity,
        status=status,
        regime=regime,
        search=search,
        limit=min(limit, 500),
        offset=offset,
    )

    return ApiResponse.success(
        data=FindingListResponse(
            items=[_to_response(r) for r in result["items"]],
            total=result["total"],
        ),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{finding_id}",
    response_model=ApiResponse[FindingResponse],
    summary="Get finding detail",
)
async def get_finding_endpoint(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FindingResponse]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    finding = await get_finding(db, finding_id=finding_id, tenant_id=tenant_id)
    if not finding:
        raise HTTPException(
            status_code=404,
            detail={"code": "FINDING_NOT_FOUND", "message": "Finding not found"},
        )

    return ApiResponse.success(
        data=_to_response(finding),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/{finding_id}",
    response_model=ApiResponse[FindingResponse],
    summary="Update finding status, assignment, notes",
)
async def update_finding_endpoint(
    finding_id: str,
    request: Request,
    body: UpdateFindingRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FindingResponse]:
    tenant_id: str = request.state.tenant_id
    user_id: str = request.state.user_id
    await set_tenant_context(db, tenant_id)

    try:
        updated = await update_finding(
            db,
            finding_id=finding_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status=body.status,
            assigned_to=str(body.assigned_to) if body.assigned_to else None,
            due_date=body.due_date,
            notes=body.notes,
            note=body.note,
        )
    except ValueError as exc:
        code = str(exc).split(":")[0]
        msg = str(exc)
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": msg},
        ) from exc

    await write_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="FINDING_UPDATED",
        resource_type="finding",
        resource_id=finding_id,
        request_id=getattr(request.state, "request_id", None),
        changes=body.model_dump(exclude_none=True),
    )

    return ApiResponse.success(
        data=_to_response(updated),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{finding_id}/activity",
    response_model=ApiResponse[list[FindingActivityResponse]],
    summary="Get finding activity timeline",
)
async def get_finding_activity(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[FindingActivityResponse]]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)

    # Verify finding belongs to this tenant
    finding = await get_finding(db, finding_id=finding_id, tenant_id=tenant_id)
    if not finding:
        raise HTTPException(status_code=404, detail={"code": "FINDING_NOT_FOUND", "message": "Finding not found"})

    result = await db.execute(
        text(
            """
            SELECT id, actor_type, actor_id, action, from_status, to_status, note, created_at
            FROM findings_activity
            WHERE finding_id = :fid AND tenant_id = :tid
            ORDER BY created_at ASC
            """
        ),
        {"fid": finding_id, "tid": tenant_id},
    )
    items = [
        FindingActivityResponse(
            id=str(row["id"]),
            actor_type=row["actor_type"],
            actor_id=str(row["actor_id"]) if row["actor_id"] else None,
            action=row["action"],
            from_status=row["from_status"],
            to_status=row["to_status"],
            note=row["note"],
            created_at=row["created_at"],
        )
        for row in result.mappings().all()
    ]

    return ApiResponse.success(
        data=items,
        request_id=getattr(request.state, "request_id", None),
    )


def _to_response(row: dict) -> FindingResponse:
    return FindingResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        audit_run_id=str(row["audit_run_id"]),
        control_id=row["control_id"],
        control_name=row["control_name"],
        regime=row["regime"],
        jurisdiction=row["jurisdiction"],
        verdict=row["verdict"],
        severity=row["severity"],
        status=row["status"],
        finding=row["finding"],
        requirement=row.get("requirement"),
        gap=row.get("gap"),
        risk=row.get("risk"),
        recommended_action=row.get("recommended_action"),
        regulatory_reference=row.get("regulatory_reference"),
        assigned_to=str(row["assigned_to"]) if row.get("assigned_to") else None,
        due_date=row.get("due_date"),
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
