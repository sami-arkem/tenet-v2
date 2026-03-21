"""
Monitoring router — Bible §12.
"""
from __future__ import annotations

import json as _json
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


class MonitoringConfigPatch(BaseModel):
    config_key: Optional[str] = None
    config_value: Optional[dict] = None
    enabled: Optional[bool] = None


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
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid"]
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
            SELECT id, severity, title,
                   COALESCE(body, '') as summary,
                   jurisdiction, regime, url,
                   effective_date, is_read, source, created_at
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
        data={"items": items, "total": total,
              "unread_count": sum(1 for i in items if not i.get("is_read"))}
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
            SELECT id, title, COALESCE(body, '') as body, severity,
                   jurisdiction, regime, url as source_url,
                   is_read, effective_date, created_at
            FROM regulatory_alerts
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
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
    updates: dict = {}
    if body.is_read is not None:
        updates["is_read"] = body.is_read
    if not updates:
        raise HTTPException(status_code=422, detail={"code": "NO_UPDATES", "message": "No fields to update"})

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = alert_id
    row = await db.execute(
        text(f"""
            UPDATE regulatory_alerts
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
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
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid"]
    params: dict = {"limit": limit, "offset": offset}

    if status:
        conditions.append("status = :status")
        params["status"] = status.upper()

    where = " AND ".join(conditions)
    rows = await db.execute(
        text(f"""
            SELECT id, title, description, jurisdiction, regime,
                   recurrence, due_date, status,
                   assigned_to, created_at, updated_at
            FROM compliance_obligations
            WHERE {where}
            ORDER BY due_date ASC NULLS LAST
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
    return ApiResponse.success(data={"items": items, "total": total}).model_dump()


@router.get("/config")
async def get_monitoring_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    row = await db.execute(
        text("""
            SELECT id, config_key, config_value, enabled, created_at, updated_at
            FROM monitoring_config
            WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
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
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=422, detail={"code": "NO_UPDATES", "message": "No fields to update"})

    existing = await db.execute(
        text("SELECT id FROM monitoring_config WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid LIMIT 1")
    )
    cv = _json.dumps(data.get("config_value", {})) if "config_value" in data else "{}"
    ck = data.get("config_key", "default")
    en = data.get("enabled", True)

    if existing.fetchone():
        set_parts = ["updated_at = NOW()"]
        if "config_key" in data:
            set_parts.append("config_key = :ck")
        if "config_value" in data:
            set_parts.append("config_value = CAST(:cv AS JSONB)")
        if "enabled" in data:
            set_parts.append("enabled = :en")
        await db.execute(
            text("UPDATE monitoring_config SET " + ", ".join(set_parts) +
                 " WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid"),
            {"ck": ck, "cv": cv, "en": en},
        )
    else:
        config_id = str(uuid4())
        await db.execute(
            text("""
                INSERT INTO monitoring_config (id, tenant_id, config_key, config_value, enabled)
                VALUES (:id, current_setting('app.current_tenant_id', TRUE)::uuid,
                        :ck, CAST(:cv AS JSONB), :en)
            """),
            {"id": config_id, "ck": ck, "cv": cv, "en": en},
        )
    await db.commit()
    return ApiResponse.success(data={"updated": True}).model_dump()
