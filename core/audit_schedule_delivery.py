from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


DELIVERY_SCHEMA_VERSION = "1.0"


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
class QueueEntry:
    queue_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    execution_date: str
    source_execution_id: str
    source_policy_hash: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OutboxEntry:
    outbox_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    event_kind: str
    target_date: str
    source_event_id: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessAlert:
    alert_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    severity: str
    reason: str
    due_date: Optional[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessSnapshot:
    schema_version: str
    cycle_date: str
    total_executions: int
    total_notifications: int
    total_alerts: int
    stale_evidence_alerts: int
    invalid_configuration_alerts: int
    schedule_disabled_alerts: int
    readiness_blocked: bool
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DeliveryState:
    emitted_queue_ids: List[str] = field(default_factory=list)
    emitted_outbox_ids: List[str] = field(default_factory=list)
    emitted_alert_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "emitted_queue_ids": sorted(set(self.emitted_queue_ids)),
            "emitted_outbox_ids": sorted(set(self.emitted_outbox_ids)),
            "emitted_alert_ids": sorted(set(self.emitted_alert_ids)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "DeliveryState":
        return cls(
            emitted_queue_ids=[str(x) for x in payload.get("emitted_queue_ids", [])],
            emitted_outbox_ids=[str(x) for x in payload.get("emitted_outbox_ids", [])],
            emitted_alert_ids=[str(x) for x in payload.get("emitted_alert_ids", [])],
        )


@dataclass(frozen=True)
class DeliveryResult:
    schema_version: str
    queue_entries: List[QueueEntry] = field(default_factory=list)
    outbox_entries: List[OutboxEntry] = field(default_factory=list)
    readiness_alerts: List[ReadinessAlert] = field(default_factory=list)
    readiness_snapshot: Optional[ReadinessSnapshot] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "queue_entries": [item.to_dict() for item in self.queue_entries],
            "outbox_entries": [item.to_dict() for item in self.outbox_entries],
            "readiness_alerts": [item.to_dict() for item in self.readiness_alerts],
            "readiness_snapshot": (
                self.readiness_snapshot.to_dict() if self.readiness_snapshot is not None else None
            ),
        }


def load_delivery_state(path: Path) -> DeliveryState:
    if not path.exists():
        return DeliveryState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DeliveryState.from_dict(payload)


def save_delivery_state(path: Path, state: DeliveryState) -> None:
    _write_json(path, state.to_dict())


def _queue_id(execution: Dict[str, object]) -> str:
    return str(execution["execution_id"])


def _outbox_id(event: Dict[str, object]) -> str:
    return str(event["event_id"])


def _alert_id(skip: Dict[str, object]) -> str:
    due_date = str(skip.get("due_date") or "none")
    return f'{skip["tenant_id"]}:{skip["audit_kind"]}:{skip["schedule_id"]}:{skip["skip_reason"]}:{due_date}'


def _severity_for_skip_reason(reason: str) -> str:
    if reason in {"STALE_EVIDENCE", "INVALID_CONFIGURATION"}:
        return "HIGH"
    if reason == "SCHEDULE_DISABLED":
        return "MEDIUM"
    return "LOW"


def _build_queue_entry(execution: Dict[str, object]) -> QueueEntry:
    return QueueEntry(
        queue_id=str(execution["execution_id"]),
        tenant_id=str(execution["tenant_id"]),
        audit_kind=str(execution["audit_kind"]),
        schedule_id=str(execution["schedule_id"]),
        due_date=str(execution["due_date"]),
        execution_date=str(execution["execution_date"]),
        source_execution_id=str(execution["execution_id"]),
        source_policy_hash=str(execution["source_policy_hash"]),
        payload_hash=_stable_json_hash(execution),
    )


def _build_outbox_entry(event: Dict[str, object]) -> OutboxEntry:
    return OutboxEntry(
        outbox_id=str(event["event_id"]),
        tenant_id=str(event["tenant_id"]),
        audit_kind=str(event["audit_kind"]),
        schedule_id=str(event["schedule_id"]),
        event_kind=str(event["event_kind"]),
        target_date=str(event["target_date"]),
        source_event_id=str(event["event_id"]),
        payload_hash=_stable_json_hash(event),
    )


def _build_readiness_alert(skip: Dict[str, object]) -> Optional[ReadinessAlert]:
    reason = str(skip["skip_reason"])
    if reason not in {"STALE_EVIDENCE", "INVALID_CONFIGURATION", "SCHEDULE_DISABLED"}:
        return None
    return ReadinessAlert(
        alert_id=_alert_id(skip),
        tenant_id=str(skip["tenant_id"]),
        audit_kind=str(skip["audit_kind"]),
        schedule_id=str(skip["schedule_id"]),
        severity=_severity_for_skip_reason(reason),
        reason=reason,
        due_date=str(skip["due_date"]) if skip.get("due_date") is not None else None,
        payload_hash=_stable_json_hash(skip),
    )


def _build_readiness_snapshot(
    runtime_cycle: Dict[str, object],
    queue_entries: List[QueueEntry],
    outbox_entries: List[OutboxEntry],
    readiness_alerts: List[ReadinessAlert],
) -> ReadinessSnapshot:
    stale = sum(1 for item in readiness_alerts if item.reason == "STALE_EVIDENCE")
    invalid = sum(1 for item in readiness_alerts if item.reason == "INVALID_CONFIGURATION")
    disabled = sum(1 for item in readiness_alerts if item.reason == "SCHEDULE_DISABLED")

    blocking_reasons: List[str] = []
    if stale:
        blocking_reasons.append(f"stale_evidence:{stale}")
    if invalid:
        blocking_reasons.append(f"invalid_configuration:{invalid}")
    if disabled:
        blocking_reasons.append(f"schedule_disabled:{disabled}")

    return ReadinessSnapshot(
        schema_version=DELIVERY_SCHEMA_VERSION,
        cycle_date=str(runtime_cycle["cycle_date"]),
        total_executions=len(queue_entries),
        total_notifications=len(outbox_entries),
        total_alerts=len(readiness_alerts),
        stale_evidence_alerts=stale,
        invalid_configuration_alerts=invalid,
        schedule_disabled_alerts=disabled,
        readiness_blocked=bool(blocking_reasons),
        blocking_reasons=blocking_reasons,
    )


def build_delivery_artifacts(
    runtime_cycle: Dict[str, object],
    *,
    state: Optional[DeliveryState] = None,
) -> Tuple[DeliveryResult, DeliveryState]:
    current_state = state or DeliveryState()
    emitted_queue_ids: Set[str] = set(current_state.emitted_queue_ids)
    emitted_outbox_ids: Set[str] = set(current_state.emitted_outbox_ids)
    emitted_alert_ids: Set[str] = set(current_state.emitted_alert_ids)

    queue_entries: List[QueueEntry] = []
    outbox_entries: List[OutboxEntry] = []
    readiness_alerts: List[ReadinessAlert] = []

    for execution in runtime_cycle.get("executions", []):
        assert isinstance(execution, dict)
        queue_id = _queue_id(execution)
        if queue_id in emitted_queue_ids:
            continue
        queue_entries.append(_build_queue_entry(execution))
        emitted_queue_ids.add(queue_id)

    for event in runtime_cycle.get("reminder_events", []):
        assert isinstance(event, dict)
        outbox_id = _outbox_id(event)
        if outbox_id in emitted_outbox_ids:
            continue
        outbox_entries.append(_build_outbox_entry(event))
        emitted_outbox_ids.add(outbox_id)

    for event in runtime_cycle.get("skip_events", []):
        assert isinstance(event, dict)
        outbox_id = _outbox_id(event)
        if outbox_id in emitted_outbox_ids:
            continue
        outbox_entries.append(_build_outbox_entry(event))
        emitted_outbox_ids.add(outbox_id)

    for skip in runtime_cycle.get("skipped", []):
        assert isinstance(skip, dict)
        alert = _build_readiness_alert(skip)
        if alert is None:
            continue
        if alert.alert_id in emitted_alert_ids:
            continue
        readiness_alerts.append(alert)
        emitted_alert_ids.add(alert.alert_id)

    queue_entries.sort(key=lambda x: (x.tenant_id, x.audit_kind, x.schedule_id, x.due_date))
    outbox_entries.sort(key=lambda x: (x.tenant_id, x.audit_kind, x.schedule_id, x.event_kind, x.target_date))
    readiness_alerts.sort(key=lambda x: (x.tenant_id, x.audit_kind, x.schedule_id, x.reason, x.due_date or ""))

    snapshot = _build_readiness_snapshot(runtime_cycle, queue_entries, outbox_entries, readiness_alerts)

    result = DeliveryResult(
        schema_version=DELIVERY_SCHEMA_VERSION,
        queue_entries=queue_entries,
        outbox_entries=outbox_entries,
        readiness_alerts=readiness_alerts,
        readiness_snapshot=snapshot,
    )
    next_state = DeliveryState(
        emitted_queue_ids=sorted(emitted_queue_ids),
        emitted_outbox_ids=sorted(emitted_outbox_ids),
        emitted_alert_ids=sorted(emitted_alert_ids),
    )
    return result, next_state


def append_delivery_outputs(
    *,
    result: DeliveryResult,
    queue_path: Path,
    outbox_path: Path,
    alerts_path: Path,
) -> None:
    existing_queue = _read_jsonl(queue_path)
    existing_outbox = _read_jsonl(outbox_path)
    existing_alerts = _read_jsonl(alerts_path)

    seen_queue = {str(row["queue_id"]) for row in existing_queue}
    seen_outbox = {str(row["outbox_id"]) for row in existing_outbox}
    seen_alerts = {str(row["alert_id"]) for row in existing_alerts}

    for item in result.queue_entries:
        row = item.to_dict()
        if row["queue_id"] not in seen_queue:
            existing_queue.append(row)
            seen_queue.add(str(row["queue_id"]))

    for item in result.outbox_entries:
        row = item.to_dict()
        if row["outbox_id"] not in seen_outbox:
            existing_outbox.append(row)
            seen_outbox.add(str(row["outbox_id"]))

    for item in result.readiness_alerts:
        row = item.to_dict()
        if row["alert_id"] not in seen_alerts:
            existing_alerts.append(row)
            seen_alerts.add(str(row["alert_id"]))

    existing_queue.sort(key=lambda x: (x["tenant_id"], x["audit_kind"], x["schedule_id"], x["due_date"]))
    existing_outbox.sort(key=lambda x: (x["tenant_id"], x["audit_kind"], x["schedule_id"], x["event_kind"], x["target_date"]))
    existing_alerts.sort(key=lambda x: (x["tenant_id"], x["audit_kind"], x["schedule_id"], x["reason"], x.get("due_date") or ""))

    _write_jsonl(queue_path, existing_queue)
    _write_jsonl(outbox_path, existing_outbox)
    _write_jsonl(alerts_path, existing_alerts)


def write_readiness_snapshot(path: Path, snapshot: ReadinessSnapshot) -> None:
    _write_json(path, snapshot.to_dict())
