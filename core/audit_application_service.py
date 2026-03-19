from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from apps.api.schemas.audits import (
    AuditDetail,
    AuditRunSummary,
    AuditSummary,
    FindingsSummary,
    ReleaseSummary,
    TriggerAuditRunResponse,
)


AUDIT_APPLICATION_SERVICE_SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


@dataclass(frozen=True)
class AuditApplicationPaths:
    audit_registry: str
    audit_runs: str
    audit_findings: str
    release_surface_dir: str
    finalize_dir: str
    remediation_dir: str
    e2e_dir: str


def default_paths(base: str = "state") -> AuditApplicationPaths:
    return AuditApplicationPaths(
        audit_registry=f"{base}/audits/audit_registry.jsonl",
        audit_runs=f"{base}/audits/audit_runs.jsonl",
        audit_findings=f"{base}/audits/audit_findings.jsonl",
        release_surface_dir=f"{base}/release_surface",
        finalize_dir=f"{base}/finalize",
        remediation_dir=f"{base}/remediation",
        e2e_dir=f"{base}/e2e",
    )


def _load_registry(paths: AuditApplicationPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.audit_registry))
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["audit_id"]))
    return rows


def _write_registry(paths: AuditApplicationPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["audit_id"]))
    _write_jsonl(Path(paths.audit_registry), rows)


def _load_runs(paths: AuditApplicationPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.audit_runs))
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["created_at"], row["run_id"]))
    return rows


def _write_runs(paths: AuditApplicationPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_id"], row["created_at"], row["run_id"]))
    _write_jsonl(Path(paths.audit_runs), rows)


def _load_findings(paths: AuditApplicationPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.audit_findings))
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["finding_id"]))
    return rows


def _write_findings(paths: AuditApplicationPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_id"], row["finding_id"]))
    _write_jsonl(Path(paths.audit_findings), rows)


def _find_audit(registry: List[Dict[str, object]], audit_id: str) -> Dict[str, object]:
    for row in registry:
        if str(row["audit_id"]) == audit_id:
            return row
    raise ValueError(f"Audit not found: {audit_id}")


def _require_same_tenant(actor_tenant_id: str, row: Dict[str, object]) -> None:
    if str(row["tenant_id"]) != actor_tenant_id:
        raise PermissionError("Forbidden")


def _deployment_decision_from_reason_output(reason_output: Optional[Dict[str, object]]) -> str:
    if not reason_output:
        return "UNKNOWN"
    return str(
        reason_output.get("deployment_decision")
        or reason_output.get("deterministic_decision")
        or "UNKNOWN"
    ).upper()


def _reason_output_path(paths: AuditApplicationPaths, audit_id: str) -> Path:
    return Path(paths.e2e_dir) / audit_id / "raw_reason_output.json"


def _run_result_path(paths: AuditApplicationPaths, audit_id: str) -> Path:
    return Path(paths.e2e_dir) / audit_id / "run_result.json"


def _release_surface_path(paths: AuditApplicationPaths, audit_id: str) -> Path:
    return Path(paths.release_surface_dir) / audit_id / "release_surface.json"


def _finalization_receipt_path(paths: AuditApplicationPaths, audit_id: str) -> Path:
    return Path(paths.finalize_dir) / audit_id / "finalization_receipt.json"


def _remediation_gate_path(paths: AuditApplicationPaths, audit_id: str) -> Path:
    return Path(paths.remediation_dir) / audit_id / "remediation_gate.json"


def _ensure_audit_container(paths: AuditApplicationPaths, audit_id: str) -> None:
    _reason_output_path(paths, audit_id).parent.mkdir(parents=True, exist_ok=True)
    _release_surface_path(paths, audit_id).parent.mkdir(parents=True, exist_ok=True)
    _finalization_receipt_path(paths, audit_id).parent.mkdir(parents=True, exist_ok=True)
    _remediation_gate_path(paths, audit_id).parent.mkdir(parents=True, exist_ok=True)


def create_audit(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    actor_user_id: str,
    payload: Dict[str, object],
) -> AuditSummary:
    registry = _load_registry(paths)
    now = _now_iso()
    audit_id = f"{tenant_id}:{payload['audit_kind']}:{payload['entity_id']}:{now}"

    row = {
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": str(payload["audit_kind"]),
        "entity_id": str(payload["entity_id"]),
        "system_name": str(payload["system_name"]),
        "jurisdiction": str(payload["jurisdiction"]),
        "framework": str(payload["framework"]),
        "status": "CREATED",
        "deployment_decision": "UNKNOWN",
        "release_ready": False,
        "report_ready": False,
        "export_ready": False,
        "finalization_ready": False,
        "scheduled_date": payload.get("scheduled_date"),
        "note": payload.get("note"),
        "created_by_user_id": actor_user_id,
        "latest_run_id": None,
        "created_at": now,
        "updated_at": now,
    }
    row["payload_hash"] = _stable_json_hash(row)

    registry.append(row)
    _write_registry(paths, registry)
    _ensure_audit_container(paths, audit_id)

    return AuditSummary(
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        audit_kind=row["audit_kind"],
        entity_id=row["entity_id"],
        system_name=row["system_name"],
        jurisdiction=row["jurisdiction"],
        framework=row["framework"],
        status=row["status"],
        deployment_decision=row["deployment_decision"],
        release_ready=row["release_ready"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_audits(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
) -> List[AuditSummary]:
    registry = _load_registry(paths)
    scoped = [row for row in registry if str(row["tenant_id"]) == tenant_id]
    return [
        AuditSummary(
            audit_id=row["audit_id"],
            tenant_id=row["tenant_id"],
            audit_kind=row["audit_kind"],
            entity_id=row["entity_id"],
            system_name=row["system_name"],
            jurisdiction=row["jurisdiction"],
            framework=row["framework"],
            status=row["status"],
            deployment_decision=row["deployment_decision"],
            release_ready=bool(row["release_ready"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in scoped
    ]


def get_audit_detail(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> AuditDetail:
    registry = _load_registry(paths)
    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    return AuditDetail(
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        audit_kind=row["audit_kind"],
        entity_id=row["entity_id"],
        system_name=row["system_name"],
        jurisdiction=row["jurisdiction"],
        framework=row["framework"],
        status=row["status"],
        deployment_decision=row["deployment_decision"],
        release_ready=bool(row["release_ready"]),
        report_ready=bool(row.get("report_ready", False)),
        export_ready=bool(row.get("export_ready", False)),
        finalization_ready=bool(row.get("finalization_ready", False)),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        note=row.get("note"),
        latest_run_id=row.get("latest_run_id"),
    )


def trigger_audit_run(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> TriggerAuditRunResponse:
    registry = _load_registry(paths)
    runs = _load_runs(paths)

    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    now = _now_iso()
    run_id = f"{audit_id}:run:{now}"

    run_row = {
        "run_id": run_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "status": "QUEUED",
        "deployment_decision": "UNKNOWN",
        "report_ready": False,
        "export_ready": False,
        "finalization_ready": False,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    run_row["payload_hash"] = _stable_json_hash(run_row)
    runs.append(run_row)
    _write_runs(paths, runs)

    row["status"] = "QUEUED"
    row["latest_run_id"] = run_id
    row["updated_at"] = now
    row["payload_hash"] = _stable_json_hash(row)
    _write_registry(paths, registry)

    return TriggerAuditRunResponse(
        audit_id=audit_id,
        run_id=run_id,
        queue_status="QUEUED",
        message="Deterministic audit run queued",
    )


def sync_audit_run_from_artifacts(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> AuditRunSummary:
    registry = _load_registry(paths)
    runs = _load_runs(paths)

    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    latest_run_id = row.get("latest_run_id")
    if not latest_run_id:
        raise ValueError(f"No run found for audit: {audit_id}")

    run_row = None
    for candidate in runs:
        if str(candidate["run_id"]) == str(latest_run_id):
            run_row = candidate
            break
    if run_row is None:
        raise ValueError(f"Run not found: {latest_run_id}")

    reason_output = _read_json(_reason_output_path(paths, audit_id))
    run_result = _read_json(_run_result_path(paths, audit_id))
    release_surface = _read_json(_release_surface_path(paths, audit_id))
    finalization_receipt = _read_json(_finalization_receipt_path(paths, audit_id))

    deployment_decision = _deployment_decision_from_reason_output(reason_output)
    release_ready = bool(release_surface.get("release_ready", False))
    finalization_ready = bool(finalization_receipt.get("finalization_ready", False))
    status = "COMPLETED" if finalization_ready else "BLOCKED"

    now = _now_iso()
    run_row.update({
        "status": status,
        "deployment_decision": deployment_decision,
        "report_ready": bool(run_result.get("report_ready", False) or release_surface.get("report_ready", False)),
        "export_ready": bool(run_result.get("export_ready", False) or release_surface.get("export_ready", False)),
        "finalization_ready": finalization_ready,
        "started_at": run_row.get("started_at") or run_row["created_at"],
        "completed_at": now,
        "updated_at": now,
    })
    run_row["payload_hash"] = _stable_json_hash(run_row)
    _write_runs(paths, runs)

    row.update({
        "status": status,
        "deployment_decision": deployment_decision,
        "release_ready": release_ready,
        "report_ready": bool(run_row["report_ready"]),
        "export_ready": bool(run_row["export_ready"]),
        "finalization_ready": finalization_ready,
        "updated_at": now,
    })
    row["payload_hash"] = _stable_json_hash(row)
    _write_registry(paths, registry)

    return AuditRunSummary(
        run_id=run_row["run_id"],
        audit_id=run_row["audit_id"],
        tenant_id=run_row["tenant_id"],
        status=run_row["status"],
        deployment_decision=run_row["deployment_decision"],
        report_ready=bool(run_row["report_ready"]),
        export_ready=bool(run_row["export_ready"]),
        finalization_ready=bool(run_row["finalization_ready"]),
        started_at=run_row.get("started_at"),
        completed_at=run_row.get("completed_at"),
    )


def get_run_summary(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> AuditRunSummary:
    registry = _load_registry(paths)
    runs = _load_runs(paths)

    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    latest_run_id = row.get("latest_run_id")
    if not latest_run_id:
        raise ValueError(f"No run found for audit: {audit_id}")

    for run_row in runs:
        if str(run_row["run_id"]) == str(latest_run_id):
            return AuditRunSummary(
                run_id=run_row["run_id"],
                audit_id=run_row["audit_id"],
                tenant_id=run_row["tenant_id"],
                status=run_row["status"],
                deployment_decision=run_row["deployment_decision"],
                report_ready=bool(run_row["report_ready"]),
                export_ready=bool(run_row["export_ready"]),
                finalization_ready=bool(run_row["finalization_ready"]),
                started_at=run_row.get("started_at"),
                completed_at=run_row.get("completed_at"),
            )

    raise ValueError(f"Run not found: {latest_run_id}")


def upsert_findings_from_reason_output(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> FindingsSummary:
    registry = _load_registry(paths)
    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    reason_output = _read_json(_reason_output_path(paths, audit_id))
    if not reason_output:
        raise ValueError(f"Reason output not found for audit: {audit_id}")

    findings_rows = _load_findings(paths)
    findings_rows = [f for f in findings_rows if not (str(f["audit_id"]) == audit_id and str(f["tenant_id"]) == tenant_id)]

    findings = reason_output.get("findings", [])
    missing_controls_count = int(reason_output.get("missing_controls_count", len(reason_output.get("missing_controls", [])) if isinstance(reason_output.get("missing_controls"), list) else 0))
    missing_evidence_count = int(reason_output.get("missing_evidence_count", len(reason_output.get("missing_evidence", [])) if isinstance(reason_output.get("missing_evidence"), list) else 0))
    blocking_reasons = [str(x) for x in reason_output.get("blocking_reasons", [])]

    for idx, finding in enumerate(findings):
        payload = {
            "finding_id": f"{audit_id}:finding:{idx+1}",
            "audit_id": audit_id,
            "tenant_id": tenant_id,
            "finding_type": str(finding.get("finding_type", "GENERAL")),
            "title": str(finding.get("title", f"Finding {idx+1}")),
            "detail": str(finding.get("detail", "")),
            "severity": str(finding.get("severity", "MEDIUM")),
        }
        payload["payload_hash"] = _stable_json_hash(payload)
        findings_rows.append(payload)

    _write_findings(paths, findings_rows)

    return FindingsSummary(
        audit_id=audit_id,
        total_findings=len(findings),
        total_missing_controls=missing_controls_count,
        total_missing_evidence=missing_evidence_count,
        blocking_reasons=blocking_reasons,
    )


def get_release_summary(
    *,
    paths: AuditApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> ReleaseSummary:
    registry = _load_registry(paths)
    row = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, row)

    release_surface = _read_json(_release_surface_path(paths, audit_id))
    finalization_receipt = _read_json(_finalization_receipt_path(paths, audit_id))
    remediation_gate = _read_json(_remediation_gate_path(paths, audit_id))

    return ReleaseSummary(
        audit_id=audit_id,
        release_status=str(release_surface.get("release_status", "BLOCKED")),
        release_ready=bool(release_surface.get("release_ready", False)),
        finalization_status=str(finalization_receipt.get("finalization_status", "BLOCKED")),
        finalization_ready=bool(finalization_receipt.get("finalization_ready", False)),
        remediation_gate_status=str(remediation_gate.get("gate_status")) if remediation_gate else None,
        remediation_ready=bool(remediation_gate.get("remediation_ready")) if remediation_gate else None,
        blocking_reasons=[str(x) for x in release_surface.get("blocking_reasons", [])] + [str(x) for x in finalization_receipt.get("blocking_reasons", [])],
    )
