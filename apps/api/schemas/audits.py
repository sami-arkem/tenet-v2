from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


AuditStatus = Literal[
    "CREATED",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "BLOCKED",
]

DeploymentDecision = Literal[
    "APPROVED",
    "CONDITIONALLY_APPROVED",
    "BLOCKED",
    "UNKNOWN",
]


class CreateAuditRequest(BaseModel):
    audit_kind: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    system_name: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    framework: str = Field(min_length=1)
    scheduled_date: Optional[str] = None
    note: Optional[str] = None


class AuditSummary(BaseModel):
    audit_id: str
    tenant_id: str
    audit_kind: str
    entity_id: str
    system_name: str
    jurisdiction: str
    framework: str
    status: AuditStatus
    deployment_decision: DeploymentDecision
    release_ready: bool
    created_at: str
    updated_at: str


class AuditDetail(BaseModel):
    audit_id: str
    tenant_id: str
    audit_kind: str
    entity_id: str
    system_name: str
    jurisdiction: str
    framework: str
    status: AuditStatus
    deployment_decision: DeploymentDecision
    release_ready: bool
    report_ready: bool
    export_ready: bool
    finalization_ready: bool
    created_at: str
    updated_at: str
    note: Optional[str] = None
    latest_run_id: Optional[str] = None


class TriggerAuditRunResponse(BaseModel):
    audit_id: str
    run_id: str
    queue_status: str
    message: str


class AuditRunSummary(BaseModel):
    run_id: str
    audit_id: str
    tenant_id: str
    status: str
    deployment_decision: DeploymentDecision
    report_ready: bool
    export_ready: bool
    finalization_ready: bool
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class FindingsSummary(BaseModel):
    audit_id: str
    total_findings: int
    total_missing_controls: int
    total_missing_evidence: int
    blocking_reasons: List[str]


class ReleaseSummary(BaseModel):
    audit_id: str
    release_status: str
    release_ready: bool
    finalization_status: str
    finalization_ready: bool
    remediation_gate_status: Optional[str] = None
    remediation_ready: Optional[bool] = None
    blocking_reasons: List[str]
