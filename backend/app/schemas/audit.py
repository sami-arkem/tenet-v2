"""
Audit-related Pydantic schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAuditRequest(BaseModel):
    entity_id: Optional[UUID] = None
    jurisdiction: str = Field(..., min_length=2, max_length=3)
    regime_scope: list[str] = Field(..., min_length=1)
    company_profile: dict = Field(default_factory=dict)
    evidence_ids: list[UUID] = Field(default_factory=list)
    force: bool = False                     # bypass evidence completeness check


class AuditRunResponse(BaseModel):
    id: str
    tenant_id: str
    entity_id: Optional[str] = None
    status: str
    jurisdiction: str
    regime_scope: list[str]
    overall_verdict: Optional[str] = None
    posture: Optional[str] = None
    control_count: int
    pass_count: int
    partial_count: int
    fail_count: int
    missing_count: int
    na_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    gold_case_version: Optional[str] = None
    model_version: str


class AuditListResponse(BaseModel):
    items: list[AuditRunResponse]
    total: int
    limit: int
    offset: int
