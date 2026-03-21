"""
Audit-related Pydantic schemas — matches frontend AuditSummary / AuditDetail types.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateAuditRequest(BaseModel):
    audit_kind: str = Field(..., min_length=1)
    entity_id: Optional[str] = None
    system_name: str = Field(..., min_length=1)
    jurisdiction: str = Field(..., min_length=1)
    framework: str = Field(..., min_length=1)
    scheduled_date: Optional[str] = None
    note: Optional[str] = None
    regime_scope: list[str] = Field(default_factory=list)
    company_profile: dict = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    force: bool = False


class AuditSummaryResponse(BaseModel):
    """Matches frontend AuditSummary type exactly."""
    audit_id: str
    tenant_id: str
    audit_kind: str
    entity_id: Optional[str] = None
    system_name: str
    jurisdiction: str
    framework: str
    status: str
    deployment_decision: str = "UNKNOWN"
    release_ready: bool = False
    created_at: datetime
    updated_at: datetime
    overall_verdict: Optional[str] = None
    posture: Optional[str] = None
    control_count: int = 0
    pass_count: int = 0
    partial_count: int = 0
    fail_count: int = 0
    missing_count: int = 0
    na_count: int = 0
    latest_run_id: Optional[str] = None
    note: Optional[str] = None


class AuditListResponse(BaseModel):
    items: list[AuditSummaryResponse]
    total: int
    limit: int
    offset: int
