"""
Monitoring router — Bible §12.
GET /v1/monitoring/alerts          → regulatory alerts for tenant
GET /v1/monitoring/alerts/{id}     → single alert
PATCH /v1/monitoring/alerts/{id}   → mark read / dismiss
GET /v1/monitoring/obligations     → compliance obligations
GET /v1/monitoring/config          → monitoring configuration
PATCH /v1/monitoring/config        → update monitoring config
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.schemas.response import ApiResponse

router = APIRouter()


class AlertPatch(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class MonitoringConfigPatch(BaseModel):
    jurisdictions: Optional[list[str]] = None
    regime_scope: Optional[list[str]] = None
    alert_email: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/alerts")
async def list_alerts(
    request: Request,
    is_read: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)"]
    params: dict = {"limit": limit, "offset": offset}

    if is_read is not None:
        conditions.append("is_read = :is_read")
        params["is_read"] = is_read
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity.upper()

    where = " AND ".join(conditions)
    rows = await db.execute(
        text(f"""
            SELECT id, severity, title, summary, jurisdiction, regime,
                   source_url, effective_date, is_read, created_at
            FROM regulatory_alerts
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM regulatory_alerts WHERE {where}"),
        params,
    )
    total = count_row.scalar() or 0
    items = [dict(r) for r in rows.mappings()]

    return ApiResponse.success(
        data={"items": items, "total": total, "unread_count": sum(1 for i in items if not i["is_read"])}
    ).model_dump()


@router.get("/alerts/{alert_id}")
async def get_alert(
    request: Request,
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    row = await db.execute(
        text("""
            SELECT * FROM regulatory_alerts
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
        """),
        {"id": alert_id},
    )
    alert = row.mappings().fetchone()
    if not alert:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Alert not found"})

    return ApiResponse.success(data=dict(alert)).model_dump()


@router.patch("/alerts/{alert_id}")
async def patch_alert(
    request: Request,
    alert_id: str,
    body: AlertPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    updates = {}
    if body.is_read is not None:
        updates["is_read"] = body.is_read
    if not updates:
        raise HTTPException(status_code=422, detail={"code": "NO_UPDATES", "message": "No fields to update"})

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = alert_id

    row = await db.execute(
        text(f"""
            UPDATE regulatory_alerts SET {set_clause}
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
            RETURNING id
        """),
        updates,
    )
    if not row.fetchone():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Alert not found"})

    await db.commit()
    return ApiResponse.success(data={"updated": True}).model_dump()


@router.get("/obligations")
async def list_obligations(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)"]
    params: dict = {"limit": limit, "offset": offset}

    if status:
        conditions.append("status = :status")
        params["status"] = status.upper()

    where = " AND ".join(conditions)
    rows = await db.execute(
        text(f"""
            SELECT id, title, description, jurisdiction, regime, frequency,
                   next_due_date, last_filed_date, status, is_overdue, filing_url
            FROM compliance_obligations
            WHERE {where}
            ORDER BY next_due_date ASC NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM compliance_obligations WHERE {where}"),
        params,
    )
    total = count_row.scalar() or 0
    items = [dict(r) for r in rows.mappings()]

    return ApiResponse.success(
        data={"items": items, "total": total}
    ).model_dump()


@router.get("/config")
async def get_monitoring_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    row = await db.execute(
        text("""
            SELECT id, jurisdictions, regime_scope, alert_email, is_active, created_at, updated_at
            FROM monitoring_config
            WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)
            LIMIT 1
        """),
    )
    config = row.mappings().fetchone()
    if not config:
        return ApiResponse.success(data={"configured": False}).model_dump()

    return ApiResponse.success(data=dict(config)).model_dump()


@router.patch("/config")
async def update_monitoring_config(
    request: Request,
    body: MonitoringConfigPatch,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail={"code": "NO_UPDATES", "message": "No fields to update"})

    # Upsert monitoring config
    existing = await db.execute(
        text("SELECT id FROM monitoring_config WHERE tenant_id = current_setting('app.current_tenant_id', TRUE) LIMIT 1")
    )
    if existing.fetchone():
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        await db.execute(
            text(f"UPDATE monitoring_config SET {set_clause} WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)"),
            updates,
        )
    else:
        config_id = str(uuid4())
        cols = ", ".join(["id", "tenant_id"] + list(updates.keys()))
        placeholders = ", ".join([":id", "current_setting('app.current_tenant_id', TRUE)"] + [f":{k}" for k in updates])
        await db.execute(
            text(f"INSERT INTO monitoring_config ({cols}) VALUES ({placeholders})"),
            {"id": config_id, **updates},
        )

    await db.commit()
    return ApiResponse.success(data={"updated": True}).model_dump()
