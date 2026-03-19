from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


DETERMINISTIC_AUDIT_EXECUTION_SCHEMA_VERSION = "1.0"


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
class DeterministicAuditExecutionRecord:
    execution_id: str
    job_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    creation_date: str
    run_status: str
    execution_status: str
    verdict_status: str
    deterministic_engine: str
    source_job_id: str
    report_ready: bool
    export_ready: bool
    release_ready: bool
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DeterministicAuditExecutionIndex:
    schema_version: str
    total_jobs_seen: int
    total_new_execution_records: int
    total_existing_execution_records: int
    total_completed_executions: int
    total_open_executions: int
    total_blocked_executions: int
    tenant_counts: Dict[str, int]
    audit_kind_counts: Dict[str, int]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DeterministicAuditExecutionState:
    emitted_execution_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {"emitted_execution_ids": sorted(set(self.emitted_execution_ids))}

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "DeterministicAuditExecutionState":
        return cls(
            emitted_execution_ids=[str(x) for x in payload.get("emitted_execution_ids", [])],
        )


@dataclass(frozen=True)
class DeterministicAuditExecutionResult:
    schema_version: str
    created_execution_records: List[DeterministicAuditExecutionRecord] = field(default_factory=list)
    execution_index: Optional[DeterministicAuditExecutionIndex] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "created_execution_records": [item.to_dict() for item in self.created_execution_records],
            "execution_index": self.execution_index.to_dict() if self.execution_index is not None else None,
        }


def load_execution_state(path: Path) -> DeterministicAuditExecutionState:
    if not path.exists():
        return DeterministicAuditExecutionState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DeterministicAuditExecutionState.from_dict(payload)


def save_execution_state(path: Path, state: DeterministicAuditExecutionState) -> None:
    _write_json(path, state.to_dict())


def load_jobs(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    return rows


def load_existing_execution_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"]))
    return rows


def load_execution_outcomes(path: Path) -> Dict[str, Dict[str, object]]:
    payload = _read_json(path)
    raw = payload.get("job_outcomes", {})
    if not isinstance(raw, dict):
        return {}
    normalized: Dict[str, Dict[str, object]] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            normalized[str(key)] = value
    return normalized


def _execution_id_from_job(job: Dict[str, object]) -> str:
    return str(job["job_id"])


def _count_by_key(rows: List[Dict[str, object]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _build_execution_record(
    *,
    job: Dict[str, object],
    outcome: Optional[Dict[str, object]],
) -> DeterministicAuditExecutionRecord:
    blocking_reasons: List[str] = []

    if outcome is None:
        run_status = "QUEUED"
        execution_status = "PENDING_EXECUTION"
        verdict_status = "NOT_RUN"
        report_ready = False
        export_ready = False
        release_ready = False
        blocking_reasons.append("deterministic_execution:not_run")
    else:
        run_status = str(outcome.get("run_status", "UNKNOWN")).upper()
        execution_status = str(outcome.get("execution_status", "UNKNOWN")).upper()
        verdict_status = str(outcome.get("verdict_status", "UNKNOWN")).upper()
        report_ready = bool(outcome.get("report_ready", False))
        export_ready = bool(outcome.get("export_ready", False))
        release_ready = bool(outcome.get("release_ready", False))
        blocking_reasons = [str(x) for x in outcome.get("blocking_reasons", [])]

        if run_status not in {"COMPLETED", "FAILED", "QUEUED", "RUNNING"}:
            run_status = "FAILED"
            if "deterministic_execution:invalid_run_status" not in blocking_reasons:
                blocking_reasons.append("deterministic_execution:invalid_run_status")

        if execution_status not in {"COMPLETED", "BLOCKED", "NOT_STARTED", "RUNNING", "FAILED", "PENDING_EXECUTION"}:
            execution_status = "FAILED"
            if "deterministic_execution:invalid_execution_status" not in blocking_reasons:
                blocking_reasons.append("deterministic_execution:invalid_execution_status")

        if run_status != "COMPLETED":
            report_ready = False
            export_ready = False
            release_ready = False
            if "deterministic_execution:not_completed" not in blocking_reasons:
                blocking_reasons.append("deterministic_execution:not_completed")

        if execution_status != "COMPLETED":
            release_ready = False
            if "deterministic_execution:execution_not_completed" not in blocking_reasons:
                blocking_reasons.append("deterministic_execution:execution_not_completed")

        if not report_ready and "report_surface:report_not_ready" not in blocking_reasons:
            blocking_reasons.append("report_surface:report_not_ready")

        if not export_ready and "export_surface:export_not_ready" not in blocking_reasons:
            blocking_reasons.append("export_surface:export_not_ready")

        if release_ready and blocking_reasons:
            release_ready = False

    payload = {
        "execution_id": str(job["job_id"]),
        "job_id": str(job["job_id"]),
        "audit_id": str(job["audit_id"]),
        "tenant_id": str(job["tenant_id"]),
        "audit_kind": str(job["audit_kind"]),
        "schedule_id": str(job["schedule_id"]),
        "due_date": str(job["due_date"]),
        "creation_date": str(job["creation_date"]),
        "run_status": run_status,
        "execution_status": execution_status,
        "verdict_status": verdict_status,
        "deterministic_engine": "reason.py",
        "source_job_id": str(job["job_id"]),
        "report_ready": report_ready,
        "export_ready": export_ready,
        "release_ready": release_ready,
        "blocking_reasons": sorted(dict.fromkeys(blocking_reasons)),
    }

    return DeterministicAuditExecutionRecord(
        execution_id=payload["execution_id"],
        job_id=payload["job_id"],
        audit_id=payload["audit_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        due_date=payload["due_date"],
        creation_date=payload["creation_date"],
        run_status=payload["run_status"],
        execution_status=payload["execution_status"],
        verdict_status=payload["verdict_status"],
        deterministic_engine=payload["deterministic_engine"],
        source_job_id=payload["source_job_id"],
        report_ready=payload["report_ready"],
        export_ready=payload["export_ready"],
        release_ready=payload["release_ready"],
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def build_execution_outputs(
    *,
    jobs: List[Dict[str, object]],
    execution_outcomes: Optional[Dict[str, Dict[str, object]]] = None,
    existing_execution_records: Optional[List[Dict[str, object]]] = None,
    state: Optional[DeterministicAuditExecutionState] = None,
) -> Tuple[DeterministicAuditExecutionResult, DeterministicAuditExecutionState]:
    current_state = state or DeterministicAuditExecutionState()
    existing_rows = existing_execution_records or []
    outcomes = execution_outcomes or {}

    emitted_execution_ids: Set[str] = set(current_state.emitted_execution_ids)
    existing_execution_ids: Set[str] = {str(row["execution_id"]) for row in existing_rows}

    created_execution_records: List[DeterministicAuditExecutionRecord] = []

    for job in jobs:
        assert isinstance(job, dict)
        execution_id = _execution_id_from_job(job)
        if execution_id in emitted_execution_ids or execution_id in existing_execution_ids:
            emitted_execution_ids.add(execution_id)
            existing_execution_ids.add(execution_id)
            continue

        outcome = outcomes.get(execution_id)
        created = _build_execution_record(job=job, outcome=outcome)
        created_execution_records.append(created)
        emitted_execution_ids.add(execution_id)
        existing_execution_ids.add(execution_id)

    created_execution_records.sort(
        key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date, item.execution_id)
    )

    combined_rows: List[Dict[str, object]] = list(existing_rows) + [record.to_dict() for record in created_execution_records]
    combined_rows.sort(
        key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"])
    )

    total_completed_executions = sum(1 for row in combined_rows if str(row.get("execution_status")) == "COMPLETED")
    total_open_executions = sum(1 for row in combined_rows if str(row.get("execution_status")) != "COMPLETED")
    total_blocked_executions = sum(
        1
        for row in combined_rows
        if str(row.get("execution_status")) in {"BLOCKED", "FAILED", "PENDING_EXECUTION", "NOT_STARTED"}
    )

    index_payload = {
        "schema_version": DETERMINISTIC_AUDIT_EXECUTION_SCHEMA_VERSION,
        "total_jobs_seen": len(jobs),
        "total_new_execution_records": len(created_execution_records),
        "total_existing_execution_records": len(combined_rows),
        "total_completed_executions": total_completed_executions,
        "total_open_executions": total_open_executions,
        "total_blocked_executions": total_blocked_executions,
        "tenant_counts": _count_by_key(combined_rows, "tenant_id"),
        "audit_kind_counts": _count_by_key(combined_rows, "audit_kind"),
    }
    execution_index = DeterministicAuditExecutionIndex(
        schema_version=index_payload["schema_version"],
        total_jobs_seen=index_payload["total_jobs_seen"],
        total_new_execution_records=index_payload["total_new_execution_records"],
        total_existing_execution_records=index_payload["total_existing_execution_records"],
        total_completed_executions=index_payload["total_completed_executions"],
        total_open_executions=index_payload["total_open_executions"],
        total_blocked_executions=index_payload["total_blocked_executions"],
        tenant_counts=index_payload["tenant_counts"],
        audit_kind_counts=index_payload["audit_kind_counts"],
        payload_hash=_stable_json_hash(index_payload),
    )

    result = DeterministicAuditExecutionResult(
        schema_version=DETERMINISTIC_AUDIT_EXECUTION_SCHEMA_VERSION,
        created_execution_records=created_execution_records,
        execution_index=execution_index,
    )
    next_state = DeterministicAuditExecutionState(emitted_execution_ids=sorted(emitted_execution_ids))
    return result, next_state


def append_execution_records(*, records: List[DeterministicAuditExecutionRecord], path: Path) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["execution_id"]) for row in existing}

    for record in records:
        row = record.to_dict()
        if row["execution_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["execution_id"]))

    existing.sort(
        key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"])
    )
    _write_jsonl(path, existing)


def write_execution_index(path: Path, execution_index: DeterministicAuditExecutionIndex) -> None:
    _write_json(path, execution_index.to_dict())
