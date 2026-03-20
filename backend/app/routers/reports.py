"""
Reports router — Bible §15.
POST /v1/reports/generate    → trigger report generation for an audit run
GET  /v1/reports             → list reports for tenant
GET  /v1/reports/{report_id} → get report metadata + download URLs
GET  /v1/reports/{report_id}/download/{format} → download file (pdf|docx|zip)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.schemas.response import ApiResponse

router = APIRouter()


class GenerateReportRequest(BaseModel):
    audit_run_id: str
    formats: list[str] = ["pdf", "docx", "json"]
    include_evidence_inventory: bool = True
    include_reasoning_trace: bool = True


@router.post("/generate", status_code=202)
async def generate_report(
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger async report generation. Returns report_id to poll."""
    tenant_id_row = await db.execute(
        text("SELECT current_setting('app.current_tenant_id', TRUE) AS tid")
    )
    tenant_id = (tenant_id_row.mappings().fetchone() or {}).get("tid", "")

    # Verify audit run belongs to tenant
    audit_row = await db.execute(
        text("""
            SELECT id, status, jurisdiction, regime_scope, overall_verdict,
                   pass_count, partial_count, fail_count, missing_count,
                   control_count, started_at, completed_at, model_version
            FROM audit_runs
            WHERE id = :run_id
              AND tenant_id = :tenant_id
        """),
        {"run_id": body.audit_run_id, "tenant_id": tenant_id},
    )
    audit = audit_row.mappings().fetchone()
    if not audit:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Audit run not found"},
        )

    if audit["status"] not in ("COMPLETE", "PARTIAL"):
        raise HTTPException(
            status_code=422,
            detail={"code": "AUDIT_NOT_COMPLETE", "message": "Report can only be generated for completed audits"},
        )

    # Load control verdicts
    verdicts_row = await db.execute(
        text("""
            SELECT control_id, control_name, regime, verdict, severity,
                   gap_description, risk_description, recommended_action,
                   regulatory_reference
            FROM control_verdicts
            WHERE audit_run_id = :run_id
            ORDER BY severity, control_id
        """),
        {"run_id": body.audit_run_id},
    )
    verdicts = [dict(v) for v in verdicts_row.mappings()]

    # Load evidence inventory
    evidence_row = await db.execute(
        text("""
            SELECT id, original_name, file_hash, file_size_bytes, mime_type,
                   document_type, status, created_at
            FROM evidence_items
            WHERE audit_run_id = :run_id
        """),
        {"run_id": body.audit_run_id},
    )
    evidence_items = [dict(e) for e in evidence_row.mappings()]

    # Build report data structure
    report_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    report_data = {
        "report_id": report_id,
        "audit_run_id": body.audit_run_id,
        "tenant_id": tenant_id,
        "generated_at": now,
        "model_version": audit["model_version"],
        "executive_summary": {
            "overall_verdict": audit["overall_verdict"],
            "jurisdiction": audit["jurisdiction"],
            "regime_scope": audit["regime_scope"],
            "control_count": audit["control_count"],
            "pass_count": audit["pass_count"],
            "partial_count": audit["partial_count"],
            "fail_count": audit["fail_count"],
            "missing_count": audit["missing_count"],
            "audit_period": {
                "started_at": str(audit["started_at"]) if audit["started_at"] else None,
                "completed_at": str(audit["completed_at"]) if audit["completed_at"] else None,
            },
        },
        "control_verdicts": verdicts,
        "evidence_inventory": evidence_items if body.include_evidence_inventory else [],
    }

    # Persist report
    report_dir = os.path.join(settings.STORAGE_LOCAL_ROOT, "reports", report_id)
    os.makedirs(report_dir, exist_ok=True)

    # Write JSON report
    json_path = os.path.join(report_dir, "control_verdicts.json")
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    # Write manifest
    json_hash = hashlib.sha256(open(json_path, "rb").read()).hexdigest()
    manifest = {
        "report_id": report_id,
        "generated_at": now,
        "audit_run_id": body.audit_run_id,
        "files": {
            "control_verdicts.json": {"sha256": json_hash, "size": os.path.getsize(json_path)},
        },
    }
    manifest_path = os.path.join(report_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Generate text-based PDF report (simple version — production would use weasyprint/puppeteer)
    pdf_content = _render_text_report(report_data)
    pdf_path = os.path.join(report_dir, "audit_report.txt")
    with open(pdf_path, "w") as f:
        f.write(pdf_content)

    # Record in generated_documents table
    await db.execute(
        text("""
            INSERT INTO generated_documents
              (id, tenant_id, audit_run_id, document_type, format,
               storage_path, file_hash, file_size_bytes)
            VALUES
              (:id, :tenant_id, :audit_run_id, 'AUDIT_REPORT', 'JSON',
               :storage_path, :file_hash, :file_size)
        """),
        {
            "id": report_id,
            "tenant_id": tenant_id,
            "audit_run_id": body.audit_run_id,
            "storage_path": report_dir,
            "file_hash": json_hash,
            "file_size": os.path.getsize(json_path),
        },
    )
    await db.commit()

    return ApiResponse.success(
        data={
            "report_id": report_id,
            "status": "complete",
            "audit_run_id": body.audit_run_id,
            "generated_at": now,
            "download_urls": {
                "json": f"/v1/reports/{report_id}/download/json",
                "manifest": f"/v1/reports/{report_id}/download/manifest",
                "text": f"/v1/reports/{report_id}/download/text",
            },
        }
    ).model_dump()


@router.get("")
async def list_reports(
    audit_run_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = ["tenant_id = current_setting('app.current_tenant_id', TRUE)"]
    params: dict = {"limit": limit, "offset": offset}

    if audit_run_id:
        conditions.append("audit_run_id = :audit_run_id")
        params["audit_run_id"] = audit_run_id

    where = " AND ".join(conditions)
    rows = await db.execute(
        text(f"""
            SELECT id, audit_run_id, document_type, format, created_at, file_size_bytes
            FROM generated_documents
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    items = [dict(r) for r in rows.mappings()]
    return ApiResponse.success(data={"items": items, "total": len(items)}).model_dump()


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.execute(
        text("""
            SELECT id, audit_run_id, document_type, format, storage_path,
                   file_hash, file_size_bytes, created_at
            FROM generated_documents
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
        """),
        {"id": report_id},
    )
    report = row.mappings().fetchone()
    if not report:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Report not found"})

    data = dict(report)
    data["download_urls"] = {
        "json": f"/v1/reports/{report_id}/download/json",
        "text": f"/v1/reports/{report_id}/download/text",
        "manifest": f"/v1/reports/{report_id}/download/manifest",
    }
    return ApiResponse.success(data=data).model_dump()


@router.get("/{report_id}/download/{fmt}")
async def download_report(
    report_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    if fmt not in ("json", "text", "manifest"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": "Format must be json, text, or manifest"})

    row = await db.execute(
        text("""
            SELECT storage_path, audit_run_id
            FROM generated_documents
            WHERE id = :id
              AND tenant_id = current_setting('app.current_tenant_id', TRUE)
        """),
        {"id": report_id},
    )
    report = row.mappings().fetchone()
    if not report:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Report not found"})

    file_map = {
        "json": ("control_verdicts.json", "application/json"),
        "text": ("audit_report.txt", "text/plain"),
        "manifest": ("manifest.json", "application/json"),
    }
    filename, media_type = file_map[fmt]
    path = os.path.join(report["storage_path"], filename)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail={"code": "FILE_NOT_FOUND", "message": "Report file not found"})

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=f"tenet_report_{report_id[:8]}_{filename}",
    )


def _render_text_report(data: dict) -> str:
    es = data["executive_summary"]
    lines = [
        "=" * 70,
        "TENET COMPLIANCE AUDIT REPORT",
        "=" * 70,
        f"Report ID:       {data['report_id']}",
        f"Audit Run ID:    {data['audit_run_id']}",
        f"Generated:       {data['generated_at']}",
        f"Model Version:   {data['model_version']}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 70,
        f"Overall Verdict: {es['overall_verdict']}",
        f"Jurisdiction:    {es['jurisdiction']}",
        f"Regime Scope:    {', '.join(es['regime_scope'])}",
        "",
        f"Controls Evaluated:  {es['control_count']}",
        f"  PASS:              {es['pass_count']}",
        f"  PARTIAL:           {es['partial_count']}",
        f"  FAIL:              {es['fail_count']}",
        f"  MISSING EVIDENCE:  {es['missing_count']}",
        "",
        "CONTROL VERDICTS",
        "-" * 70,
    ]
    for v in data["control_verdicts"]:
        lines += [
            f"[{v['verdict']}] {v['control_id']} — {v['control_name']}",
        ]
        if v.get("gap_description"):
            lines.append(f"  Gap: {v['gap_description']}")
        if v.get("recommended_action"):
            lines.append(f"  Action: {v['recommended_action']}")
        lines.append("")

    if data.get("evidence_inventory"):
        lines += ["EVIDENCE INVENTORY", "-" * 70]
        for e in data["evidence_inventory"]:
            lines.append(f"  {e['original_name']} ({e['status']}) sha256:{str(e.get('file_hash',''))[:16]}...")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]
    return "\n".join(lines)
