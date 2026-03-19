from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


AUDIT_MATERIALIZATION_SCHEMA_VERSION = "1.0"


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
class AuditWorkflowRecord:
    audit_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    creation_date: str
    source_request_id: str
    source_queue_id: str
    source_policy_hash: str
    workflow_origin: str
    workflow_status: str
    release_ready: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MaterializationSummary:
    schema_version: str
    total_requests_seen: int
    total_records_created_now: int
    total_records_deduplicated: int
    total_records_existing_after_write: int
    materialization_complete: bool
    pending_request_ids: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FinalExecutionScheduleDependencyGate:
    schema_version: str
    gate_name: str
    gate_status: str
    dependency_ready: bool
    schedule_runtime_gate_status: str
    schedule_runtime_ready: bool
    total_requests_seen: int
    total_records_created_now: int
    total_existing_audit_records: int
    pending_request_ids: List[str]
    blocking_reasons: List[str]
    inherited_blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditMaterializationState:
    materialized_request_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "materialized_request_ids": sorted(set(self.materialized_request_ids)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "AuditMaterializationState":
        return cls(
            materialized_request_ids=[str(x) for x in payload.get("materialized_request_ids", [])],
        )


@dataclass(frozen=True)
class AuditMaterializationResult:
    schema_version: str
    created_records: List[AuditWorkflowRecord] = field(default_factory=list)
    materialization_summary: Optional[MaterializationSummary] = None
    dependency_gate: Optional[FinalExecutionScheduleDependencyGate] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "created_records": [item.to_dict() for item in self.created_records],
            "materialization_summary": (
                self.materialization_summary.to_dict() if self.materialization_summary is not None else None
            ),
            "dependency_gate": (
                self.dependency_gate.to_dict() if self.dependency_gate is not None else None
            ),
        }


def load_audit_materialization_state(path: Path) -> AuditMaterializationState:
    if not path.exists():
        return AuditMaterializationState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AuditMaterializationState.from_dict(payload)


def save_audit_materialization_state(path: Path, state: AuditMaterializationState) -> None:
    _write_json(path, state.to_dict())


def load_audit_creation_requests(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"]))
    return rows


def load_schedule_gate(path: Path) -> Dict[str, object]:
    return _read_json(path)


def load_existing_audit_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["audit_id"]))
    return rows


def _audit_id_from_request(request: Dict[str, object]) -> str:
    return f'{request["tenant_id"]}:{request["audit_kind"]}:{request["schedule_id"]}:{request["due_date"]}'


def _build_audit_workflow_record(request: Dict[str, object]) -> AuditWorkflowRecord:
    payload = {
        "audit_id": _audit_id_from_request(request),
        "tenant_id": str(request["tenant_id"]),
        "audit_kind": str(request["audit_kind"]),
        "schedule_id": str(request["schedule_id"]),
        "due_date": str(request["due_date"]),
        "creation_date": str(request["execution_date"]),
        "source_request_id": str(request["request_id"]),
        "source_queue_id": str(request["source_queue_id"]),
        "source_policy_hash": str(request["source_policy_hash"]),
        "workflow_origin": "SCHEDULE_RUNTIME",
        "workflow_status": "CREATED",
        "release_ready": False,
    }
    return AuditWorkflowRecord(
        audit_id=payload["audit_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        due_date=payload["due_date"],
        creation_date=payload["creation_date"],
        source_request_id=payload["source_request_id"],
        source_queue_id=payload["source_queue_id"],
        source_policy_hash=payload["source_policy_hash"],
        workflow_origin=payload["workflow_origin"],
        workflow_status=payload["workflow_status"],
        release_ready=payload["release_ready"],
        payload_hash=_stable_json_hash(payload),
    )


def build_audit_materialization_outputs(
    *,
    audit_creation_requests: List[Dict[str, object]],
    schedule_gate: Dict[str, object],
    existing_audit_records: Optional[List[Dict[str, object]]] = None,
    state: Optional[AuditMaterializationState] = None,
) -> Tuple[AuditMaterializationResult, AuditMaterializationState]:
    current_state = state or AuditMaterializationState()
    existing_rows = existing_audit_records or []

    materialized_request_ids: Set[str] = set(current_state.materialized_request_ids)
    existing_audit_ids: Set[str] = {str(row["audit_id"]) for row in existing_rows}

    created_records: List[AuditWorkflowRecord] = []
    deduplicated_count = 0

    for request in audit_creation_requests:
        assert isinstance(request, dict)
        request_id = str(request["request_id"])
        audit_id = _audit_id_from_request(request)

        if request_id in materialized_request_ids or audit_id in existing_audit_ids:
            deduplicated_count += 1
            materialized_request_ids.add(request_id)
            existing_audit_ids.add(audit_id)
            continue

        record = _build_audit_workflow_record(request)
        created_records.append(record)
        materialized_request_ids.add(request_id)
        existing_audit_ids.add(record.audit_id)

    created_records.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date))

    inherited_blocking_reasons = [str(x) for x in schedule_gate.get("blocking_reasons", [])]
    schedule_runtime_ready = bool(schedule_gate.get("schedule_runtime_ready", False))
    schedule_runtime_gate_status = str(schedule_gate.get("gate_status", "UNKNOWN"))

    # Check which requests were not materialized (already existed or were deduplicated)
    created_request_ids = {record.source_request_id for record in created_records}
    unresolved_request_ids: List[str] = []
    for request in audit_creation_requests:
        request_id = str(request["request_id"])
        if request_id not in created_request_ids:
            # This request was deduplicated - check if it's truly unresolved
            # If it already exists in existing_rows, it's not a blocker
            audit_id = _audit_id_from_request(request)
            already_exists = any(str(row["audit_id"]) == audit_id for row in existing_rows)
            already_materialized = request_id in current_state.materialized_request_ids
            if not already_exists and not already_materialized:
                unresolved_request_ids.append(request_id)

    blocking_reasons: List[str] = []
    blocking_reasons.extend(inherited_blocking_reasons)
    if unresolved_request_ids:
        blocking_reasons.append(f"unmaterialized_schedule_requests:{len(unresolved_request_ids)}")

    dependency_ready = schedule_runtime_ready and not unresolved_request_ids
    gate_status = "PASS" if dependency_ready else "BLOCKED"

    summary_payload = {
        "schema_version": AUDIT_MATERIALIZATION_SCHEMA_VERSION,
        "total_requests_seen": len(audit_creation_requests),
        "total_records_created_now": len(created_records),
        "total_records_deduplicated": deduplicated_count,
        "total_records_existing_after_write": len(existing_rows) + len(created_records),
        "materialization_complete": len(unresolved_request_ids) == 0,
        "pending_request_ids": unresolved_request_ids,
    }
    summary = MaterializationSummary(
        schema_version=summary_payload["schema_version"],
        total_requests_seen=summary_payload["total_requests_seen"],
        total_records_created_now=summary_payload["total_records_created_now"],
        total_records_deduplicated=summary_payload["total_records_deduplicated"],
        total_records_existing_after_write=summary_payload["total_records_existing_after_write"],
        materialization_complete=summary_payload["materialization_complete"],
        pending_request_ids=summary_payload["pending_request_ids"],
        payload_hash=_stable_json_hash(summary_payload),
    )

    gate_payload = {
        "schema_version": AUDIT_MATERIALIZATION_SCHEMA_VERSION,
        "gate_name": "final_execution_schedule_dependency_gate",
        "gate_status": gate_status,
        "dependency_ready": dependency_ready,
        "schedule_runtime_gate_status": schedule_runtime_gate_status,
        "schedule_runtime_ready": schedule_runtime_ready,
        "total_requests_seen": len(audit_creation_requests),
        "total_records_created_now": len(created_records),
        "total_existing_audit_records": len(existing_rows) + len(created_records),
        "pending_request_ids": unresolved_request_ids,
        "blocking_reasons": blocking_reasons,
        "inherited_blocking_reasons": inherited_blocking_reasons,
    }
    dependency_gate = FinalExecutionScheduleDependencyGate(
        schema_version=gate_payload["schema_version"],
        gate_name=gate_payload["gate_name"],
        gate_status=gate_payload["gate_status"],
        dependency_ready=gate_payload["dependency_ready"],
        schedule_runtime_gate_status=gate_payload["schedule_runtime_gate_status"],
        schedule_runtime_ready=gate_payload["schedule_runtime_ready"],
        total_requests_seen=gate_payload["total_requests_seen"],
        total_records_created_now=gate_payload["total_records_created_now"],
        total_existing_audit_records=gate_payload["total_existing_audit_records"],
        pending_request_ids=gate_payload["pending_request_ids"],
        blocking_reasons=gate_payload["blocking_reasons"],
        inherited_blocking_reasons=gate_payload["inherited_blocking_reasons"],
        payload_hash=_stable_json_hash(gate_payload),
    )

    result = AuditMaterializationResult(
        schema_version=AUDIT_MATERIALIZATION_SCHEMA_VERSION,
        created_records=created_records,
        materialization_summary=summary,
        dependency_gate=dependency_gate,
    )
    next_state = AuditMaterializationState(
        materialized_request_ids=sorted(materialized_request_ids),
    )
    return result, next_state


def append_audit_workflow_records(
    *,
    records: List[AuditWorkflowRecord],
    path: Path,
) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["audit_id"]) for row in existing}

    for record in records:
        row = record.to_dict()
        if row["audit_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["audit_id"]))

    existing.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["audit_id"]))
    _write_jsonl(path, existing)


def write_materialization_summary(path: Path, summary: MaterializationSummary) -> None:
    _write_json(path, summary.to_dict())


def write_final_execution_dependency_gate(path: Path, gate: FinalExecutionScheduleDependencyGate) -> None:
    _write_json(path, gate.to_dict())
