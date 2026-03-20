"""
Calendar router — Bible §3.15.
GET /v1/calendar/events  → compliance events (audits, filings, obligations)
GET /v1/calendar/upcoming → next 30 days of events
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/events")
async def get_calendar_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns compliance events from obligations, audit history, and scheduled audits.
    """
    now = datetime.now(timezone.utc)
    start_dt = datetime.fromisoformat(start) if start else now.replace(day=1)
    end_dt = datetime.fromisoformat(end) if end else (now + timedelta(days=90))

    events = []

    # Obligations with due dates in range
    if not event_type or event_type == "obligation":
        obs = await db.execute(
            text("""
                SELECT id, title, jurisdiction, regime, next_due_date, status, is_overdue
                FROM compliance_obligations
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)
                  AND next_due_date BETWEEN :start AND :end
                ORDER BY next_due_date ASC
            """),
            {"start": start_dt, "end": end_dt},
        )
        for row in obs.mappings():
            events.append({
                "id": str(row["id"]),
                "type": "obligation",
                "title": row["title"],
                "date": row["next_due_date"].isoformat() if row["next_due_date"] else None,
                "jurisdiction": row["jurisdiction"],
                "regime": row["regime"],
                "status": row["status"],
                "is_overdue": row["is_overdue"],
                "urgency": "danger" if row["is_overdue"] else "warning",
            })

    # Completed audit runs in range
    if not event_type or event_type == "audit":
        audits = await db.execute(
            text("""
                SELECT id, jurisdiction, regime_scope, overall_verdict,
                       completed_at, started_at
                FROM audit_runs
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)
                  AND completed_at BETWEEN :start AND :end
                ORDER BY completed_at DESC
            """),
            {"start": start_dt, "end": end_dt},
        )
        for row in audits.mappings():
            events.append({
                "id": str(row["id"]),
                "type": "audit",
                "title": f"Audit — {', '.join(row['regime_scope'])}",
                "date": row["completed_at"].isoformat() if row["completed_at"] else None,
                "jurisdiction": row["jurisdiction"],
                "verdict": row["overall_verdict"],
                "urgency": "brand",
            })

    # Filing submissions in range
    if not event_type or event_type == "filing":
        filings = await db.execute(
            text("""
                SELECT id, obligation_id, status, submitted_at, due_date, jurisdiction
                FROM filing_submissions
                WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)
                  AND (due_date BETWEEN :start AND :end
                       OR submitted_at BETWEEN :start AND :end)
                ORDER BY due_date ASC
            """),
            {"start": start_dt, "end": end_dt},
        )
        for row in filings.mappings():
            events.append({
                "id": str(row["id"]),
                "type": "filing",
                "title": f"Filing — {row['jurisdiction']}",
                "date": row["due_date"].isoformat() if row["due_date"] else None,
                "jurisdiction": row["jurisdiction"],
                "status": row["status"],
                "urgency": "warning",
            })

    # Sort by date
    events.sort(key=lambda e: e["date"] or "")

    return ApiResponse.success(
        data={"events": events, "total": len(events), "range": {"start": start_dt.isoformat(), "end": end_dt.isoformat()}}
    ).model_dump()


@router.get("/upcoming")
async def get_upcoming_events(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns next N days of compliance events, grouped by day."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    # Reuse the events endpoint logic
    start_str = now.isoformat()
    end_str = end.isoformat()

    # Get obligations due soon
    obs = await db.execute(
        text("""
            SELECT id, title, jurisdiction, regime, next_due_date, is_overdue
            FROM compliance_obligations
            WHERE tenant_id = current_setting('app.current_tenant_id', TRUE)
              AND next_due_date BETWEEN :start AND :end
            ORDER BY next_due_date ASC
            LIMIT 50
        """),
        {"start": now, "end": end},
    )

    upcoming = []
    for row in obs.mappings():
        due = row["next_due_date"]
        days_until = (due.date() - now.date()).days if due else 999
        upcoming.append({
            "id": str(row["id"]),
            "type": "obligation",
            "title": row["title"],
            "date": due.isoformat() if due else None,
            "days_until": days_until,
            "is_overdue": row["is_overdue"],
            "urgency": "danger" if row["is_overdue"] else ("warning" if days_until <= 7 else "brand"),
        })

    return ApiResponse.success(
        data={"upcoming": upcoming, "days_ahead": days}
    ).model_dump()
