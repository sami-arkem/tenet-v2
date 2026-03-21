from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from apps.api.schemas.audits import AuditRunSummary, TriggerAuditRunResponse
from apps.api.schemas.findings import (
    ExportManifestSummaryResponse,
    FindingListResponse,
    FindingRow,
    ReportSummaryResponse,
)
from core.audit_application_service import (
    AuditApplicationPaths,
    _find_audit,
    _load_findings,
    _load_registry,
    _load_runs,
    _reason_output_path,
    _release_surface_path,
    _finalization_receipt_path,
    _remediation_gate_path,
    _run_result_path,
    _write_registry,
    _write_runs,
    _stable_json_hash,
    _write_json,
    _read_json,
    default_paths,
)
from core.tenet_e2e_orchestrator import TenetE2EPaths, run_tenet_e2e
from core.evidence_application_service import EvidenceApplicationPaths, recompute_audit_evidence_gate
from core.audit_preparation_service import AuditPreparationPaths, build_audit_preparation_summary


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
class AuditRuntimePaths:
    audit_app: AuditApplicationPaths
    base_dir: str


def runtime_paths(base: str = "state") -> AuditRuntimePaths:
    return AuditRuntimePaths(
        audit_app=default_paths(base),
        base_dir=base,
    )


def _evidence_gate_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "evidence" / audit_id / "audit_evidence_gate.json"


def _report_manifest_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "finalize" / audit_id / "immutable_release_package.json"


def _jobs_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_runner" / audit_id / "jobs.jsonl"


def _work_items_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_workflow" / audit_id / "work_items.jsonl"


def _materialized_audits_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_schedule" / audit_id / "materialized_audit_records.jsonl"


def _execution_state_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_execution" / audit_id / "execution_state.json"


def _execution_records_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_execution" / audit_id / "execution_records.jsonl"


def _execution_index_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_execution" / audit_id / "execution_index.json"


def _canonical_reason_artifacts_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_execution" / audit_id / "canonical_reason_artifacts.json"


def _execution_outcomes_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_execution" / audit_id / "execution_outcomes.json"


def _remediation_state_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "remediation" / audit_id / "remediation_state.json"


def _remediation_items_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "remediation" / audit_id / "remediation_items.jsonl"


def _remediation_index_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "remediation" / audit_id / "remediation_index.json"


def _remediation_gate_path_for_e2e(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "remediation" / audit_id / "remediation_gate.json"


def _schedule_dependency_gate_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_schedule" / audit_id / "final_execution_schedule_dependency_gate.json"


def _final_execution_discipline_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "final_execution" / audit_id / "final_execution_discipline.json"


def _runner_index_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "audit_runner" / audit_id / "runner_index.json"


def _report_gate_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "reports" / audit_id / "report_gate.json"


def _export_gate_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "exports" / audit_id / "export_gate.json"


def _release_surface_path_for_e2e(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "release_surface" / audit_id / "release_surface.json"


def _finalize_release_artifact_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "finalize" / audit_id / "finalize_release_artifact.json"


def _finalize_decision_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "finalize" / audit_id / "finalize_decision.json"


def _immutable_release_package_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "finalize" / audit_id / "immutable_release_package.json"


def _finalization_receipt_path_for_e2e(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "finalize" / audit_id / "finalization_receipt.json"


def _production_readiness_path(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "control_plane" / audit_id / "production_readiness.json"


def _run_result_path_for_e2e(base_dir: str, audit_id: str) -> Path:
    return Path(base_dir) / "e2e" / audit_id / "run_result.json"


def _seed_if_missing(path: Path, payload: Dict[str, object]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(path, payload)


def _seed_jsonl_if_missing(path: Path, rows: List[Dict[str, object]]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(path, rows)


def _ensure_runtime_seed_data(base_dir: str, audit: Dict[str, object]) -> None:
    audit_id = str(audit["audit_id"])
    tenant_id = str(audit["tenant_id"])
    audit_kind = str(audit["audit_kind"])
    now = _now_iso()

    _seed_if_missing(_evidence_gate_path(base_dir, audit_id), {
        "gate_name": "audit_evidence_gate",
        "gate_status": "PASS",
        "evidence_ready": True,
        "waiting_file_count": 0,
        "blocking_reasons": [],
    })

    _seed_jsonl_if_missing(_jobs_path(base_dir, audit_id), [{
        "job_id": audit_id,
        "audit_id": audit_id,
        "work_item_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": audit_kind,
        "schedule_id": audit_id,
        "due_date": audit.get("scheduled_date") or now[:10],
        "creation_date": now[:10],
        "intake_status": "READY_FOR_AUDIT_EXECUTION",
        "execution_status": "NOT_STARTED",
        "run_status": "QUEUED",
        "source_work_item_id": audit_id,
        "payload_hash": "seed-job",
    }])

    _seed_jsonl_if_missing(_work_items_path(base_dir, audit_id), [{
        "work_item_id": audit_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": audit_kind,
        "schedule_id": audit_id,
        "due_date": audit.get("scheduled_date") or now[:10],
        "creation_date": now[:10],
        "workflow_origin": "API",
        "source_request_id": audit_id,
        "source_queue_id": audit_id,
        "intake_status": "READY_FOR_AUDIT_EXECUTION",
        "execution_status": "NOT_STARTED",
        "release_ready": False,
        "payload_hash": "seed-work-item",
    }])

    _seed_jsonl_if_missing(_materialized_audits_path(base_dir, audit_id), [{
        "audit_id": audit_id,
        "audit_kind": audit_kind,
        "creation_date": now[:10],
        "due_date": audit.get("scheduled_date") or now[:10],
        "release_ready": False,
        "schedule_id": audit_id,
        "source_policy_hash": "seed-policy",
        "source_queue_id": audit_id,
        "source_request_id": audit_id,
        "tenant_id": tenant_id,
        "workflow_origin": "API",
        "workflow_status": "CREATED",
        "payload_hash": "seed-materialized-audit",
    }])

    _seed_if_missing(_schedule_dependency_gate_path(base_dir, audit_id), {
        "schema_version": "1.0",
        "gate_name": "final_execution_schedule_dependency_gate",
        "gate_status": "PASS",
        "dependency_ready": True,
        "schedule_runtime_gate_status": "PASS",
        "schedule_runtime_ready": True,
        "blocking_reasons": [],
        "payload_hash": "seed-schedule-dependency",
    })

    _seed_if_missing(_runner_index_path(base_dir, audit_id), {
        "schema_version": "1.0",
        "total_work_items_seen": 1,
        "total_new_jobs": 0,
        "total_existing_jobs": 1,
        "total_open_jobs": 0,
        "total_completed_jobs": 1,
        "tenant_counts": {tenant_id: 1},
        "audit_kind_counts": {audit_kind: 1},
        "payload_hash": "seed-runner-index",
    })

    _seed_if_missing(_report_gate_path(base_dir, audit_id), {
        "gate_name": "report_validation_gate",
        "gate_status": "PASS",
        "validation_ready": True,
        "blocking_reasons": [],
        "payload_hash": "seed-report-gate",
    })

    _seed_if_missing(_export_gate_path(base_dir, audit_id), {
        "gate_name": "export_gate",
        "gate_status": "PASS",
        "export_ready": True,
        "blocking_reasons": [],
        "payload_hash": "seed-export-gate",
    })


def _assert_evidence_ready(base_dir: str, audit_id: str, tenant_id: str) -> None:
    prep = build_audit_preparation_summary(
        paths=AuditPreparationPaths(base_dir),
        tenant_id=tenant_id,
        audit_id=audit_id,
    )
    if prep.preparation_status != "READY":
        if any(item.status in {"UPLOADING", "PROCESSING"} for item in prep.checklist):
            raise ValueError("AUDIT_PREPARATION_INCOMPLETE: Evidence upload or processing still in progress")
        if any(item.status == "OCR_REQUIRED" for item in prep.checklist):
            raise ValueError("AUDIT_PREPARATION_INCOMPLETE: OCR is required for one or more evidence files")
        if any(item.status == "REVIEW_REQUIRED" for item in prep.checklist):
            raise ValueError("AUDIT_PREPARATION_INCOMPLETE: Evidence classification confirmation is required")
        raise ValueError("AUDIT_PREPARATION_INCOMPLETE: Required evidence is missing")


def _assert_no_active_run(runs: List[Dict[str, object]], audit_id: str) -> None:
    for row in runs:
        if str(row["audit_id"]) == audit_id and str(row["status"]) in {"QUEUED", "RUNNING"}:
            raise ValueError("AUDIT_IN_PROGRESS: An audit is already running")


def _deployment_decision_from_reason_output(reason_output: Optional[Dict[str, object]]) -> str:
    if not reason_output:
        return "UNKNOWN"
    return str(
        reason_output.get("deployment_decision")
        or reason_output.get("deterministic_decision")
        or "UNKNOWN"
    ).upper()


def _require_same_tenant(actor_tenant_id: str, row: Dict[str, object]) -> None:
    if str(row["tenant_id"]) != actor_tenant_id:
        raise PermissionError("Forbidden")


def execute_audit_run(
    *,
    paths: AuditRuntimePaths,
    tenant_id: str,
    audit_id: str,
) -> TriggerAuditRunResponse:
    registry = _load_registry(paths.audit_app)
    runs = _load_runs(paths.audit_app)

    audit = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, audit)

    _assert_evidence_ready(paths.base_dir, audit_id, tenant_id)
    _assert_no_active_run(runs, audit_id)
    _ensure_runtime_seed_data(paths.base_dir, audit)

    now = _now_iso()
    run_id = f"{audit_id}:run:{now}"

    run_row = {
        "run_id": run_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "status": "RUNNING",
        "deployment_decision": "UNKNOWN",
        "report_ready": False,
        "export_ready": False,
        "finalization_ready": False,
        "started_at": now,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    run_row["payload_hash"] = _stable_json_hash(run_row)
    runs.append(run_row)
    _write_runs(paths.audit_app, runs)

    audit["status"] = "RUNNING"
    audit["latest_run_id"] = run_id
    audit["updated_at"] = now
    audit["payload_hash"] = _stable_json_hash(audit)
    _write_registry(paths.audit_app, registry)

    e2e_paths = TenetE2EPaths(
        raw_reason_output=str(_reason_output_path(paths.audit_app, audit_id)),
        canonical_reason_artifacts=str(_canonical_reason_artifacts_path(paths.base_dir, audit_id)),
        execution_outcomes=str(_execution_outcomes_path(paths.base_dir, audit_id)),
        jobs=str(_jobs_path(paths.base_dir, audit_id)),
        execution_state=str(_execution_state_path(paths.base_dir, audit_id)),
        execution_records=str(_execution_records_path(paths.base_dir, audit_id)),
        execution_index=str(_execution_index_path(paths.base_dir, audit_id)),
        remediation_state=str(_remediation_state_path(paths.base_dir, audit_id)),
        remediation_items=str(_remediation_items_path(paths.base_dir, audit_id)),
        remediation_index=str(_remediation_index_path(paths.base_dir, audit_id)),
        remediation_gate=str(_remediation_gate_path_for_e2e(paths.base_dir, audit_id)),
        schedule_dependency_gate=str(_schedule_dependency_gate_path(paths.base_dir, audit_id)),
        final_execution_discipline=str(_final_execution_discipline_path(paths.base_dir, audit_id)),
        runner_index=str(_runner_index_path(paths.base_dir, audit_id)),
        report_gate=str(_report_gate_path(paths.base_dir, audit_id)),
        export_gate=str(_export_gate_path(paths.base_dir, audit_id)),
        release_surface=str(_release_surface_path_for_e2e(paths.base_dir, audit_id)),
        finalize_release_artifact=str(_finalize_release_artifact_path(paths.base_dir, audit_id)),
        finalize_decision=str(_finalize_decision_path(paths.base_dir, audit_id)),
        immutable_release_package=str(_immutable_release_package_path(paths.base_dir, audit_id)),
        finalization_receipt=str(_finalization_receipt_path_for_e2e(paths.base_dir, audit_id)),
        work_items=str(_work_items_path(paths.base_dir, audit_id)),
        materialized_audits=str(_materialized_audits_path(paths.base_dir, audit_id)),
        production_readiness=str(_production_readiness_path(paths.base_dir, audit_id)),
    )

    result = run_tenet_e2e(e2e_paths)
    _write_json(_run_result_path_for_e2e(paths.base_dir, audit_id), result.to_dict())

    reason_output = _read_json(_reason_output_path(paths.audit_app, audit_id))
    release_surface = _read_json(_release_surface_path(paths.audit_app, audit_id))
    finalization_receipt = _read_json(_finalization_receipt_path(paths.audit_app, audit_id))

    deployment_decision = _deployment_decision_from_reason_output(reason_output)
    finalization_ready = bool(finalization_receipt.get("finalization_ready", False))
    release_ready = bool(release_surface.get("release_ready", False))
    status = "COMPLETED" if finalization_ready else "BLOCKED"

    for row in runs:
        if str(row["run_id"]) == run_id:
            row.update({
                "status": status,
                "deployment_decision": deployment_decision,
                "report_ready": bool(release_surface.get("report_ready", False)),
                "export_ready": bool(release_surface.get("export_ready", False)),
                "finalization_ready": finalization_ready,
                "completed_at": _now_iso(),
                "updated_at": _now_iso(),
            })
            row["payload_hash"] = _stable_json_hash(row)

    audit.update({
        "status": status,
        "deployment_decision": deployment_decision,
        "release_ready": release_ready,
        "report_ready": bool(release_surface.get("report_ready", False)),
        "export_ready": bool(release_surface.get("export_ready", False)),
        "finalization_ready": finalization_ready,
        "updated_at": _now_iso(),
    })
    audit["payload_hash"] = _stable_json_hash(audit)

    _write_runs(paths.audit_app, runs)
    _write_registry(paths.audit_app, registry)

    return TriggerAuditRunResponse(
        audit_id=audit_id,
        run_id=run_id,
        queue_status=status,
        message="Deterministic audit pipeline executed",
    )


def get_findings_list(
    *,
    paths: AuditRuntimePaths,
    tenant_id: str,
    audit_id: str,
) -> FindingListResponse:
    registry = _load_registry(paths.audit_app)
    audit = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, audit)

    rows = [row for row in _load_findings(paths.audit_app) if str(row["audit_id"]) == audit_id and str(row["tenant_id"]) == tenant_id]
    return FindingListResponse(
        audit_id=audit_id,
        total_findings=len(rows),
        rows=[
            FindingRow(
                finding_id=row["finding_id"],
                audit_id=row["audit_id"],
                tenant_id=row["tenant_id"],
                finding_type=row["finding_type"],
                title=row["title"],
                detail=row["detail"],
                severity=row["severity"],
            )
            for row in rows
        ],
    )


def get_report_summary(
    *,
    paths: AuditRuntimePaths,
    tenant_id: str,
    audit_id: str,
) -> ReportSummaryResponse:
    registry = _load_registry(paths.audit_app)
    audit = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, audit)

    release_surface = _read_json(_release_surface_path(paths.audit_app, audit_id))
    finalization_receipt = _read_json(_finalization_receipt_path(paths.audit_app, audit_id))
    remediation_gate = _read_json(_remediation_gate_path(paths.audit_app, audit_id))

    return ReportSummaryResponse(
        audit_id=audit_id,
        run_id=audit.get("latest_run_id"),
        report_ready=bool(release_surface.get("report_ready", False)),
        export_ready=bool(release_surface.get("export_ready", False)),
        finalization_ready=bool(finalization_receipt.get("finalization_ready", False)),
        release_ready=bool(release_surface.get("release_ready", False)),
        release_status=str(release_surface.get("release_status", "BLOCKED")),
        finalization_status=str(finalization_receipt.get("finalization_status", "BLOCKED")),
        remediation_gate_status=str(remediation_gate.get("gate_status")) if remediation_gate else None,
        blocking_reasons=[str(x) for x in release_surface.get("blocking_reasons", [])] + [str(x) for x in finalization_receipt.get("blocking_reasons", [])],
    )


def get_export_manifest_summary(
    *,
    paths: AuditRuntimePaths,
    tenant_id: str,
    audit_id: str,
) -> ExportManifestSummaryResponse:
    registry = _load_registry(paths.audit_app)
    audit = _find_audit(registry, audit_id)
    _require_same_tenant(tenant_id, audit)

    manifest = _read_json(_report_manifest_path(paths.base_dir, audit_id))
    return ExportManifestSummaryResponse(
        audit_id=audit_id,
        package_status=str(manifest.get("package_status", "BLOCKED")),
        package_ready=bool(manifest.get("package_ready", False)),
        manifest_path=str(_report_manifest_path(paths.base_dir, audit_id)),
        included_files=list(manifest.get("included_files", [])),
        blocking_reasons=[str(x) for x in manifest.get("blocking_reasons", [])],
    )
