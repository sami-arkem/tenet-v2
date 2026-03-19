from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class FindingRow(BaseModel):
    finding_id: str
    audit_id: str
    tenant_id: str
    finding_type: str
    title: str
    detail: str
    severity: str


class FindingListResponse(BaseModel):
    audit_id: str
    total_findings: int
    rows: List[FindingRow]


class ReportSummaryResponse(BaseModel):
    audit_id: str
    run_id: Optional[str]
    report_ready: bool
    export_ready: bool
    finalization_ready: bool
    release_ready: bool
    release_status: str
    finalization_status: str
    remediation_gate_status: Optional[str]
    blocking_reasons: List[str]


class ExportManifestSummaryResponse(BaseModel):
    audit_id: str
    package_status: str
    package_ready: bool
    manifest_path: str
    included_files: List[dict]
    blocking_reasons: List[str]
