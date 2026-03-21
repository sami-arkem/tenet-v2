from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


EXECUTION_BRIDGE_SCHEMA_VERSION = "1.0"


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
class AuditCreationRequest:
    request_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    execution_date: str
    source_queue_id: str
    source_policy_hash: str
    workflow_status: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleReadinessGate:
    schema_version: str
    gate_name: str
    gate_status: str
    blocking_reasons: List[str]
    blocking_alert_ids: List[str]
    stale_evidence_alerts: int
    invalid_configuration_alerts: int
    schedule_disabled_alerts: int
    total_alerts: int
    total_due_execution_requests: int
    total_notifications: int
    schedule_runtime_ready: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionBridgeState:
    emitted_request_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "emitted_request_ids": sorted(set(self.emitted_request_ids)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "ExecutionBridgeState":
        return cls(
            emitted_request_ids=[str(x) for x in payload.get("emitted_request_ids", [])],
        )


@dataclass(frozen=True)
class ExecutionBridgeResult:
    schema_version: str
    audit_creation_requests: List[AuditCreationRequest] = field(default_factory=list)
    schedule_gate: Optional[ScheduleReadinessGate] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "audit_creation_requests": [item.to_dict() for item in self.audit_creation_requests],
            "schedule_gate": self.schedule_gate.to_dict() if self.schedule_gate is not None else None,
        }


def load_execution_bridge_state(path: Path) -> ExecutionBridgeState:
    if not path.exists():
        return ExecutionBridgeState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExecutionBridgeState.from_dict(payload)


def save_execution_bridge_state(path: Path, state: ExecutionBridgeState) -> None:
    _write_json(path, state.to_dict())


def _request_id_from_queue_entry(queue_entry: Dict[str, object]) -> str:
    return str(queue_entry["queue_id"])


def _build_audit_creation_request(queue_entry: Dict[str, object]) -> AuditCreationRequest:
    request_payload = {
        "request_id": str(queue_entry["queue_id"]),
        "tenant_id": str(queue_entry["tenant_id"]),
        "audit_kind": str(queue_entry["audit_kind"]),
        "schedule_id": str(queue_entry["schedule_id"]),
        "due_date": str(queue_entry["due_date"]),
        "execution_date": str(queue_entry["execution_date"]),
        "source_queue_id": str(queue_entry["queue_id"]),
        "source_policy_hash": str(queue_entry["source_policy_hash"]),
        "workflow_status": "PENDING_AUDIT_CREATION",
    }
    return AuditCreationRequest(
        request_id=request_payload["request_id"],
        tenant_id=request_payload["tenant_id"],
        audit_kind=request_payload["audit_kind"],
        schedule_id=request_payload["schedule_id"],
        due_date=request_payload["due_date"],
        execution_date=request_payload["execution_date"],
        source_queue_id=request_payload["source_queue_id"],
        source_policy_hash=request_payload["source_policy_hash"],
        workflow_status=request_payload["workflow_status"],
        payload_hash=_stable_json_hash(request_payload),
    )


def _count_alert_reason(alerts: List[Dict[str, object]], reason: str) -> int:
    return sum(1 for alert in alerts if str(alert.get("reason")) == reason)


def build_schedule_readiness_gate(
    readiness_snapshot: Dict[str, object],
    readiness_alerts: List[Dict[str, object]],
    *,
    total_due_execution_requests: int,
) -> ScheduleReadinessGate:
    blocking_reasons = [str(x) for x in readiness_snapshot.get("blocking_reasons", [])]
    blocking_alert_ids = sorted(str(alert["alert_id"]) for alert in readiness_alerts)

    gate_payload = {
        "schema_version": EXECUTION_BRIDGE_SCHEMA_VERSION,
        "gate_name": "audit_schedule_runtime_gate",
        "gate_status": "BLOCKED" if bool(readiness_snapshot.get("readiness_blocked")) else "PASS",
        "blocking_reasons": blocking_reasons,
        "blocking_alert_ids": blocking_alert_ids,
        "stale_evidence_alerts": _count_alert_reason(readiness_alerts, "STALE_EVIDENCE"),
        "invalid_configuration_alerts": _count_alert_reason(readiness_alerts, "INVALID_CONFIGURATION"),
        "schedule_disabled_alerts": _count_alert_reason(readiness_alerts, "SCHEDULE_DISABLED"),
        "total_alerts": len(readiness_alerts),
        "total_due_execution_requests": total_due_execution_requests,
        "total_notifications": int(readiness_snapshot.get("total_notifications", 0)),
        "schedule_runtime_ready": not bool(readiness_snapshot.get("readiness_blocked")),
    }

    return ScheduleReadinessGate(
        schema_version=gate_payload["schema_version"],
        gate_name=gate_payload["gate_name"],
        gate_status=gate_payload["gate_status"],
        blocking_reasons=gate_payload["blocking_reasons"],
        blocking_alert_ids=gate_payload["blocking_alert_ids"],
        stale_evidence_alerts=gate_payload["stale_evidence_alerts"],
        invalid_configuration_alerts=gate_payload["invalid_configuration_alerts"],
        schedule_disabled_alerts=gate_payload["schedule_disabled_alerts"],
        total_alerts=gate_payload["total_alerts"],
        total_due_execution_requests=gate_payload["total_due_execution_requests"],
        total_notifications=gate_payload["total_notifications"],
        schedule_runtime_ready=gate_payload["schedule_runtime_ready"],
        payload_hash=_stable_json_hash(gate_payload),
    )


def build_execution_bridge_outputs(
    *,
    due_execution_queue: List[Dict[str, object]],
    readiness_snapshot: Dict[str, object],
    readiness_alerts: List[Dict[str, object]],
    state: Optional[ExecutionBridgeState] = None,
) -> Tuple[ExecutionBridgeResult, ExecutionBridgeState]:
    current_state = state or ExecutionBridgeState()
    emitted_request_ids: Set[str] = set(current_state.emitted_request_ids)

    audit_creation_requests: List[AuditCreationRequest] = []

    for queue_entry in due_execution_queue:
        assert isinstance(queue_entry, dict)
        request_id = _request_id_from_queue_entry(queue_entry)
        if request_id in emitted_request_ids:
            continue
        request = _build_audit_creation_request(queue_entry)
        audit_creation_requests.append(request)
        emitted_request_ids.add(request_id)

    audit_creation_requests.sort(
        key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date)
    )

    schedule_gate = build_schedule_readiness_gate(
        readiness_snapshot,
        readiness_alerts,
        total_due_execution_requests=len(audit_creation_requests),
    )

    result = ExecutionBridgeResult(
        schema_version=EXECUTION_BRIDGE_SCHEMA_VERSION,
        audit_creation_requests=audit_creation_requests,
        schedule_gate=schedule_gate,
    )
    next_state = ExecutionBridgeState(
        emitted_request_ids=sorted(emitted_request_ids),
    )
    return result, next_state


def append_audit_creation_requests(
    *,
    requests: List[AuditCreationRequest],
    path: Path,
) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["request_id"]) for row in existing}

    for request in requests:
        row = request.to_dict()
        if row["request_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["request_id"]))

    existing.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"]))
    _write_jsonl(path, existing)


def write_schedule_gate(path: Path, gate: ScheduleReadinessGate) -> None:
    _write_json(path, gate.to_dict())


def load_due_execution_queue(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"]))
    return rows


def load_readiness_alerts(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["reason"], row.get("due_date") or ""))
    return rows


def load_readiness_snapshot(path: Path) -> Dict[str, object]:
    return _read_json(path)
