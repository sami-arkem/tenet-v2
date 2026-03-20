from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FindingResponse(BaseModel):
    id: str
    tenant_id: str
    audit_run_id: str
    control_id: str
    control_name: str
    regime: str
    jurisdiction: str
    verdict: str
    severity: str
    status: str
    finding: str
    requirement: Optional[str] = None
    gap: Optional[str] = None
    risk: Optional[str] = None
    recommended_action: Optional[str] = None
    regulatory_reference: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FindingListResponse(BaseModel):
    items: list[FindingResponse]
    total: int


class UpdateFindingRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    note: Optional[str] = None          # required for status changes (min 10 chars)


class FindingActivityResponse(BaseModel):
    id: str
    actor_type: str
    actor_id: Optional[str] = None
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
