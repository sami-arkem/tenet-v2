"""
Dashboard router — Bible §3.3, §T.2.3.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.db.queries import get_dashboard_metrics
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("", summary="Get dashboard metrics for the current tenant")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """
    Returns real-time dashboard metrics:
    - open/critical/high finding counts
    - controls passing %
    - last audit status and posture
    - per-regime health
    - unread regulatory alert count
    """
    tenant_id: str = request.state.tenant_id
    await set_tenant_context(db, tenant_id)
    data = await get_dashboard_metrics(db, tenant_id=tenant_id)
    return ApiResponse.success(data=data, request_id=getattr(request.state, "request_id", None))
