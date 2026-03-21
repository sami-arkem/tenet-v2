from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PIPELINE_RECONCILER_SCHEMA_VERSION = "1.0"


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
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True)
class PipelinePhaseStatus:
    phase_name: str
    phase_status: str
    total_items: int
    completed_items: int
    blocked_items: int
    open_items: int
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProductionReadinessArtifact:
    schema_version: str
    readiness_status: str
    readiness_ready: bool
    total_work_items: int
    total_jobs: int
    total_execution_records: int
    total_completed_executions: int
    total_open_executions: int
    total_blocked_executions: int
    finalization_status: str
    finalization_ready: bool
    blocking_reasons: List[str]
    phases: List[PipelinePhaseStatus]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "readiness_status": self.readiness_status,
            "readiness_ready": self.readiness_ready,
            "total_work_items": self.total_work_items,
            "total_jobs": self.total_jobs,
            "total_execution_records": self.total_execution_records,
            "total_completed_executions": self.total_completed_executions,
            "total_open_executions": self.total_open_executions,
            "total_blocked_executions": self.total_blocked_executions,
            "finalization_status": self.finalization_status,
            "finalization_ready": self.finalization_ready,
            "blocking_reasons": self.blocking_reasons,
            "phases": [phase.to_dict() for phase in self.phases],
            "payload_hash": self.payload_hash,
        }


@dataclass(frozen=True)
class PipelineReconciliationResult:
    schema_version: str
    reconciled_work_items: List[Dict[str, object]]
    reconciled_jobs: List[Dict[str, object]]
    reconciled_materialized_audits: List[Dict[str, object]]
    production_readiness: ProductionReadinessArtifact

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "reconciled_work_items": self.reconciled_work_items,
            "reconciled_jobs": self.reconciled_jobs,
            "reconciled_materialized_audits": self.reconciled_materialized_audits,
            "production_readiness": self.production_readiness.to_dict(),
        }


def load_work_items(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))
    return rows


def load_jobs(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    return rows


def load_materialized_audit_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["audit_id"]))
    return rows


def load_execution_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"]))
    return rows


def load_artifact(path: Path) -> Dict[str, object]:
    return _read_json(path)


def _index_by(rows: List[Dict[str, object]], key: str) -> Dict[str, Dict[str, object]]:
    return {str(row[key]): row for row in rows}


def _sorted_unique(values: List[str]) -> List[str]:
    return sorted(dict.fromkeys(values))


def _reconcile_work_items(
    work_items: List[Dict[str, object]],
    execution_index: Dict[str, Dict[str, object]],
    finalization_ready: bool,
) -> List[Dict[str, object]]:
    reconciled: List[Dict[str, object]] = []

    for row in work_items:
        row = dict(row)
        execution = execution_index.get(str(row["audit_id"]))

        if execution is None:
            row["execution_status"] = "NOT_STARTED"
            row["intake_status"] = "READY_FOR_AUDIT_EXECUTION"
            row["release_ready"] = False
        else:
            row["execution_status"] = str(execution.get("execution_status", "NOT_STARTED"))
            if row["execution_status"] == "COMPLETED":
                row["intake_status"] = "AUDIT_EXECUTED"
            elif row["execution_status"] in {"BLOCKED", "FAILED"}:
                row["intake_status"] = "AUDIT_BLOCKED"
            else:
                row["intake_status"] = "AUDIT_IN_PROGRESS"
            row["release_ready"] = bool(execution.get("release_ready", False)) and finalization_ready

        row["payload_hash"] = _stable_json_hash({
            "work_item_id": row["work_item_id"],
            "audit_id": row["audit_id"],
            "tenant_id": row["tenant_id"],
            "audit_kind": row["audit_kind"],
            "schedule_id": row["schedule_id"],
            "due_date": row["due_date"],
            "creation_date": row["creation_date"],
            "workflow_origin": row["workflow_origin"],
            "source_request_id": row["source_request_id"],
            "source_queue_id": row["source_queue_id"],
            "intake_status": row["intake_status"],
            "execution_status": row["execution_status"],
            "release_ready": row["release_ready"],
        })
        reconciled.append(row)

    reconciled.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))
    return reconciled


def _reconcile_jobs(
    jobs: List[Dict[str, object]],
    execution_index: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    reconciled: List[Dict[str, object]] = []

    for row in jobs:
        row = dict(row)
        execution = execution_index.get(str(row["audit_id"]))

        if execution is None:
            row["run_status"] = "QUEUED"
            row["execution_status"] = "NOT_STARTED"
        else:
            row["run_status"] = str(execution.get("run_status", "QUEUED"))
            row["execution_status"] = str(execution.get("execution_status", "NOT_STARTED"))

        row["payload_hash"] = _stable_json_hash({
            "job_id": row["job_id"],
            "audit_id": row["audit_id"],
            "work_item_id": row["work_item_id"],
            "tenant_id": row["tenant_id"],
            "audit_kind": row["audit_kind"],
            "schedule_id": row["schedule_id"],
            "due_date": row["due_date"],
            "creation_date": row["creation_date"],
            "intake_status": row["intake_status"],
            "execution_status": row["execution_status"],
            "run_status": row["run_status"],
            "source_work_item_id": row["source_work_item_id"],
        })
        reconciled.append(row)

    reconciled.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    return reconciled


def _reconcile_materialized_audits(
    records: List[Dict[str, object]],
    execution_index: Dict[str, Dict[str, object]],
    finalization_ready: bool,
) -> List[Dict[str, object]]:
    reconciled: List[Dict[str, object]] = []

    for row in records:
        row = dict(row)
        execution = execution_index.get(str(row["audit_id"]))

        if execution is None:
            row["workflow_status"] = "CREATED"
            row["release_ready"] = False
        else:
            execution_status = str(execution.get("execution_status", "NOT_STARTED"))
            if execution_status == "COMPLETED":
                row["workflow_status"] = "EXECUTION_COMPLETED"
            elif execution_status in {"BLOCKED", "FAILED"}:
                row["workflow_status"] = "EXECUTION_BLOCKED"
            else:
                row["workflow_status"] = "EXECUTION_IN_PROGRESS"
            row["release_ready"] = bool(execution.get("release_ready", False)) and finalization_ready

        row["payload_hash"] = _stable_json_hash({
            "audit_id": row["audit_id"],
            "audit_kind": row["audit_kind"],
            "creation_date": row["creation_date"],
            "due_date": row["due_date"],
            "release_ready": row["release_ready"],
            "schedule_id": row["schedule_id"],
            "source_policy_hash": row["source_policy_hash"],
            "source_queue_id": row["source_queue_id"],
            "source_request_id": row["source_request_id"],
            "tenant_id": row["tenant_id"],
            "workflow_origin": row["workflow_origin"],
            "workflow_status": row["workflow_status"],
        })
        reconciled.append(row)

    reconciled.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["audit_id"]))
    return reconciled


def _phase_from_work_items(work_items: List[Dict[str, object]]) -> PipelinePhaseStatus:
    total = len(work_items)
    completed = sum(1 for row in work_items if str(row.get("execution_status")) == "COMPLETED")
    blocked = sum(1 for row in work_items if str(row.get("execution_status")) in {"BLOCKED", "FAILED"})
    open_items = total - completed
    blocking_reasons: List[str] = []
    if blocked > 0:
        blocking_reasons.append(f"audit_workflow:blocked:{blocked}")
    return PipelinePhaseStatus(
        phase_name="audit_workflow",
        phase_status="PASS" if total > 0 and blocked == 0 and open_items == 0 else "BLOCKED",
        total_items=total,
        completed_items=completed,
        blocked_items=blocked,
        open_items=open_items,
        blocking_reasons=blocking_reasons,
    )


def _phase_from_jobs(jobs: List[Dict[str, object]]) -> PipelinePhaseStatus:
    total = len(jobs)
    completed = sum(1 for row in jobs if str(row.get("run_status")) == "COMPLETED")
    blocked = sum(1 for row in jobs if str(row.get("run_status")) == "FAILED")
    open_items = total - completed
    blocking_reasons: List[str] = []
    if blocked > 0:
        blocking_reasons.append(f"audit_runner:failed:{blocked}")
    if open_items > 0 and blocked == 0:
        blocking_reasons.append(f"audit_runner:open:{open_items}")
    return PipelinePhaseStatus(
        phase_name="audit_runner",
        phase_status="PASS" if total > 0 and blocked == 0 and open_items == 0 else "BLOCKED",
        total_items=total,
        completed_items=completed,
        blocked_items=blocked,
        open_items=open_items,
        blocking_reasons=blocking_reasons,
    )


def _phase_from_execution_records(records: List[Dict[str, object]]) -> PipelinePhaseStatus:
    total = len(records)
    completed = sum(1 for row in records if str(row.get("execution_status")) == "COMPLETED")
    blocked = sum(1 for row in records if str(row.get("execution_status")) in {"BLOCKED", "FAILED", "PENDING_EXECUTION", "NOT_STARTED"})
    open_items = total - completed
    blocking_reasons: List[str] = []
    for row in records:
        if str(row.get("execution_status")) != "COMPLETED":
            for reason in row.get("blocking_reasons", []):
                blocking_reasons.append(str(reason))
    return PipelinePhaseStatus(
        phase_name="deterministic_execution",
        phase_status="PASS" if total > 0 and blocked == 0 and open_items == 0 else "BLOCKED",
        total_items=total,
        completed_items=completed,
        blocked_items=blocked,
        open_items=open_items,
        blocking_reasons=_sorted_unique(blocking_reasons),
    )


def _phase_from_finalization(finalization_receipt: Dict[str, object]) -> PipelinePhaseStatus:
    ready = bool(finalization_receipt.get("finalization_ready", False))
    blocking_reasons = [str(x) for x in finalization_receipt.get("blocking_reasons", [])]
    return PipelinePhaseStatus(
        phase_name="finalization",
        phase_status="PASS" if ready else "BLOCKED",
        total_items=1,
        completed_items=1 if ready else 0,
        blocked_items=0 if ready else 1,
        open_items=0 if ready else 1,
        blocking_reasons=blocking_reasons,
    )


def build_production_readiness(
    *,
    reconciled_work_items: List[Dict[str, object]],
    reconciled_jobs: List[Dict[str, object]],
    execution_records: List[Dict[str, object]],
    finalization_receipt: Dict[str, object],
) -> ProductionReadinessArtifact:
    phases = [
        _phase_from_work_items(reconciled_work_items),
        _phase_from_jobs(reconciled_jobs),
        _phase_from_execution_records(execution_records),
        _phase_from_finalization(finalization_receipt),
    ]
    phases.sort(key=lambda phase: phase.phase_name)

    total_completed_executions = sum(1 for row in execution_records if str(row.get("execution_status")) == "COMPLETED")
    total_open_executions = sum(1 for row in execution_records if str(row.get("execution_status")) != "COMPLETED")
    total_blocked_executions = sum(1 for row in execution_records if str(row.get("execution_status")) in {"BLOCKED", "FAILED", "PENDING_EXECUTION", "NOT_STARTED"})

    blocking_reasons: List[str] = []
    for phase in phases:
        for reason in phase.blocking_reasons:
            blocking_reasons.append(f"{phase.phase_name}:{reason}")

    finalization_status = str(finalization_receipt.get("finalization_status", "BLOCKED")).upper()
    finalization_ready = bool(finalization_receipt.get("finalization_ready", False))
    readiness_ready = finalization_ready and not blocking_reasons
    readiness_status = "PASS" if readiness_ready else "BLOCKED"

    payload = {
        "schema_version": PIPELINE_RECONCILER_SCHEMA_VERSION,
        "readiness_status": readiness_status,
        "readiness_ready": readiness_ready,
        "total_work_items": len(reconciled_work_items),
        "total_jobs": len(reconciled_jobs),
        "total_execution_records": len(execution_records),
        "total_completed_executions": total_completed_executions,
        "total_open_executions": total_open_executions,
        "total_blocked_executions": total_blocked_executions,
        "finalization_status": finalization_status,
        "finalization_ready": finalization_ready,
        "blocking_reasons": blocking_reasons,
        "phases": [phase.to_dict() for phase in phases],
    }

    return ProductionReadinessArtifact(
        schema_version=payload["schema_version"],
        readiness_status=payload["readiness_status"],
        readiness_ready=payload["readiness_ready"],
        total_work_items=payload["total_work_items"],
        total_jobs=payload["total_jobs"],
        total_execution_records=payload["total_execution_records"],
        total_completed_executions=payload["total_completed_executions"],
        total_open_executions=payload["total_open_executions"],
        total_blocked_executions=payload["total_blocked_executions"],
        finalization_status=payload["finalization_status"],
        finalization_ready=payload["finalization_ready"],
        blocking_reasons=payload["blocking_reasons"],
        phases=phases,
        payload_hash=_stable_json_hash(payload),
    )


def build_pipeline_reconciliation_result(
    *,
    work_items: List[Dict[str, object]],
    jobs: List[Dict[str, object]],
    materialized_audit_records: List[Dict[str, object]],
    execution_records: List[Dict[str, object]],
    finalization_receipt: Dict[str, object],
) -> PipelineReconciliationResult:
    execution_index = _index_by(execution_records, "audit_id")
    finalization_ready = bool(finalization_receipt.get("finalization_ready", False))

    reconciled_work_items = _reconcile_work_items(work_items, execution_index, finalization_ready)
    reconciled_jobs = _reconcile_jobs(jobs, execution_index)
    reconciled_materialized_audits = _reconcile_materialized_audits(materialized_audit_records, execution_index, finalization_ready)

    production_readiness = build_production_readiness(
        reconciled_work_items=reconciled_work_items,
        reconciled_jobs=reconciled_jobs,
        execution_records=execution_records,
        finalization_receipt=finalization_receipt,
    )

    return PipelineReconciliationResult(
        schema_version=PIPELINE_RECONCILER_SCHEMA_VERSION,
        reconciled_work_items=reconciled_work_items,
        reconciled_jobs=reconciled_jobs,
        reconciled_materialized_audits=reconciled_materialized_audits,
        production_readiness=production_readiness,
    )


def write_work_items(path: Path, rows: List[Dict[str, object]]) -> None:
    _write_jsonl(path, rows)


def write_jobs(path: Path, rows: List[Dict[str, object]]) -> None:
    _write_jsonl(path, rows)


def write_materialized_audits(path: Path, rows: List[Dict[str, object]]) -> None:
    _write_jsonl(path, rows)


def write_production_readiness(path: Path, artifact: ProductionReadinessArtifact) -> None:
    _write_json(path, artifact.to_dict())
