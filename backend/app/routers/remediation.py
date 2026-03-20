"""
Remediation router — Bible §T.2.7.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.db.queries import (
    get_remediation_dashboard,
    get_remediation_item,
    list_remediation_items,
    write_audit_log,
)
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/dashboard", summary="Remediation dashboard stats")
async def remediation_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)
    data = await get_remediation_dashboard(db, tenant_id=tenant_id)
    return ApiResponse.success(data=data, request_id=getattr(request.state, "request_id", None))


@router.get("", summary="List remediation items")
async def list_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)
    items = await list_remediation_items(db, tenant_id=tenant_id)
    return ApiResponse.success(data=items, request_id=getattr(request.state, "request_id", None))


@router.get("/{item_id}", summary="Get remediation item detail")
async def get_item(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)
    item = await get_remediation_item(db, item_id=item_id, tenant_id=tenant_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"code": "REMEDIATION_NOT_FOUND", "message": "Remediation item not found"},
        )
    return ApiResponse.success(data=item, request_id=getattr(request.state, "request_id", None))
