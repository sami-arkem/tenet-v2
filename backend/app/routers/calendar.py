
"""
Calendar router — Bible §3.15.
GET /v1/calendar/events  → compliance events (audits, filings, obligations)
GET /v1/calendar/upcoming → next 30 days of events
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, set_tenant_context
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/events")
async def get_calendar_events(
    request: Request,
    start: Optional[str] = None,
    end: Optional[str] = None,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    now = datetime.now(timezone.utc)
    start_dt = datetime.fromisoformat(start) if start else now.replace(day=1)
    end_dt = datetime.fromisoformat(end) if end else (now + timedelta(days=90))
    events = []

    if not event_type or event_type == "obligation":
        obs = await db.execute(
            text("""
                SELECT id, title, jurisdiction, regime, due_date, status
                FROM compliance_obligations
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                  AND due_date BETWEEN :start AND :end
                ORDER BY due_date ASC
            """),
            {"start": start_dt.date(), "end": end_dt.date()},
        )
        for row in obs.mappings():
            due = row["due_date"]
            is_overdue = due is not None and due < now.date() and row["status"] != "completed"
            events.append({
                "id": str(row["id"]),
                "type": "obligation",
                "title": row["title"],
                "date": due.isoformat() if due else None,
                "jurisdiction": row["jurisdiction"],
                "regime": row["regime"],
                "status": row["status"],
                "is_overdue": is_overdue,
                "urgency": "danger" if is_overdue else "warning",
            })

    if not event_type or event_type == "audit":
        audits = await db.execute(
            text("""
                SELECT id, jurisdiction, regime_scope, overall_verdict, completed_at
                FROM audit_runs
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                  AND completed_at BETWEEN :start AND :end
                ORDER BY completed_at DESC
            """),
            {"start": start_dt, "end": end_dt},
        )
        for row in audits.mappings():
            events.append({
                "id": str(row["id"]),
                "type": "audit",
                "title": "Audit — " + (row["regime_scope"] or ""),
                "date": row["completed_at"].isoformat() if row["completed_at"] else None,
                "jurisdiction": row["jurisdiction"],
                "verdict": row["overall_verdict"],
                "urgency": "brand",
            })

    if not event_type or event_type == "calendar":
        cal_events = await db.execute(
            text("""
                SELECT id, title, event_type, event_date, regime, jurisdiction, is_completed
                FROM calendar_events
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                  AND event_date BETWEEN :start AND :end
                ORDER BY event_date ASC
            """),
            {"start": start_dt.date(), "end": end_dt.date()},
        )
        for row in cal_events.mappings():
            events.append({
                "id": str(row["id"]),
                "type": row["event_type"] or "calendar",
                "title": row["title"],
                "date": row["event_date"].isoformat() if row["event_date"] else None,
                "jurisdiction": row["jurisdiction"],
                "regime": row["regime"],
                "is_completed": row["is_completed"],
                "urgency": "brand",
            })

    events.sort(key=lambda e: e.get("date") or "")
    return ApiResponse.success(
        data={"events": events, "total": len(events)}
    ).model_dump()


@router.get("/upcoming")
async def get_upcoming_events(
    request: Request,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, request.state.tenant_id)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    obs = await db.execute(
        text("""
            SELECT id, title, jurisdiction, regime, due_date, status
            FROM compliance_obligations
            WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
              AND due_date BETWEEN :start AND :end
            ORDER BY due_date ASC
            LIMIT 50
        """),
        {"start": now.date(), "end": end.date()},
    )
    upcoming = []
    for row in obs.mappings():
        due = row["due_date"]
        is_overdue = due is not None and due < now.date()
        days_until = (due - now.date()).days if due else 999
        upcoming.append({
            "id": str(row["id"]),
            "type": "obligation",
            "title": row["title"],
            "date": due.isoformat() if due else None,
            "days_until": days_until,
            "is_overdue": is_overdue,
            "urgency": "danger" if is_overdue else ("warning" if days_until <= 7 else "brand"),
        })
    return ApiResponse.success(data={"upcoming": upcoming, "days_ahead": days}).model_dump()
