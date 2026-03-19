from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.audit_pipeline import (
    build_execution_bundle,
    result_to_snapshot,
    run_audit_from_payload,
)
from core.export_package import export_audit_package
from core.report_renderer import render_report_bundle


DEFAULT_EXPORT_ROOT = Path("artifacts") / "audit_packages"


class AuditExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    create_export_package: bool = Field(
        default=False,
        description="When true, create an immutable export package from the canonical runtime output.",
    )
    export_root: str | None = Field(
        default=None,
        description="Optional export root directory. Defaults to artifacts/audit_packages.",
    )
    package_name: str | None = Field(
        default=None,
        description="Optional explicit package directory name.",
    )
    package_version: str = Field(
        default="v1",
        description="Export package schema version.",
    )


class AuditExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] = Field(..., description="Canonical deterministic audit input payload")
    export: AuditExportOptions | None = Field(
        default=None,
        description="Optional export package controls.",
    )


class ExportPackageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    package_paths: dict[str, str]
    manifest: dict[str, Any]
    verification: dict[str, Any]
    topline: dict[str, Any]


class AuditExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic_audit_result: dict[str, Any]
    report_pack: dict[str, Any]
    report_bundle: dict[str, Any]
    snapshot: dict[str, Any]
    topline: dict[str, Any]
    export_package: ExportPackageResponse | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    service: str
    mode: str


app = FastAPI(
    title="Tenet Deterministic Audit API",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def _resolve_export_root(export: AuditExportOptions | None) -> Path:
    if export is None or export.export_root is None:
        return DEFAULT_EXPORT_ROOT

    root = Path(export.export_root)
    if root.is_absolute():
        raise ValueError("export.export_root must be a relative path")
    if ".." in root.parts:
        raise ValueError("export.export_root must not contain parent traversal")
    return root


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        service="tenet-deterministic-audit-api",
        mode="deterministic",
    )


@app.post("/v1/audits/execute", response_model=AuditExecutionResponse)
def execute_audit(request: AuditExecutionRequest) -> AuditExecutionResponse:
    try:
        result = run_audit_from_payload(request.payload)
        execution_bundle = build_execution_bundle(request.payload)
        report_bundle = render_report_bundle(result)
        snapshot = result_to_snapshot(result)

        export_package_response: ExportPackageResponse | None = None
        export_options = request.export

        if export_options and export_options.create_export_package:
            export_out = export_audit_package(
                payload=request.payload,
                export_root=_resolve_export_root(export_options),
                package_name=export_options.package_name,
                package_version=export_options.package_version,
            )
            export_package_response = ExportPackageResponse(**export_out)

        return AuditExecutionResponse(
            deterministic_audit_result=execution_bundle["deterministic_audit_result"],
            report_pack=execution_bundle["report_pack"],
            report_bundle=report_bundle,
            snapshot=snapshot,
            topline=execution_bundle["topline"],
            export_package=export_package_response,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"deterministic audit execution failed: {exc}") from exc
