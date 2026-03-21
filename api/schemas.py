from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class MetaBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    timestamp: str
    version: str = "1.0"


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    data: T | None
    meta: MetaBody
    error: ErrorBody | None


class AuditExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    create_export_package: bool = False
    export_root: str | None = None
    package_name: str | None = None
    package_version: str = "v1"


class AuditCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]
    export: AuditExportOptions | None = None


class AuditCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    snapshot: dict[str, Any]
    topline: dict[str, Any]
    export_package: dict[str, Any] | None = None


class AuditDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    deterministic_audit_result: dict[str, Any]
    report_pack: dict[str, Any]
    report_bundle: dict[str, Any]
    snapshot: dict[str, Any]
    topline: dict[str, Any]
    export_package: dict[str, Any] | None = None


class AuditListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    company_name: str | None
    audit_type: str | None
    overall_posture: str | None
    deployment_decision: str | None
    created_at: str | None


class AuditListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AuditListItem]


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    markdown: str
    deployment_decision: str
    overall_posture: str
    finding_count: int
    remediation_count: int


class ExportPackageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    package_paths: dict[str, str]
    manifest: dict[str, Any]
    verification: dict[str, Any]
    topline: dict[str, Any]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    service: str
    mode: str
