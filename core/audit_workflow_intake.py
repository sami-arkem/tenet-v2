from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


AUDIT_WORKFLOW_INTAKE_SCHEMA_VERSION = "1.0"


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
class AuditWorkflowWorkItem:
    work_item_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    creation_date: str
    workflow_origin: str
    source_request_id: str
    source_queue_id: str
    intake_status: str
    execution_status: str
    release_ready: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditWorkflowIndex:
    schema_version: str
    total_records_seen: int
    total_new_work_items: int
    total_existing_work_items: int
    total_open_work_items: int
    total_release_ready: int
    tenant_counts: Dict[str, int]
    audit_kind_counts: Dict[str, int]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditWorkflowIntakeState:
    emitted_work_item_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "emitted_work_item_ids": sorted(set(self.emitted_work_item_ids)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "AuditWorkflowIntakeState":
        return cls(
            emitted_work_item_ids=[str(x) for x in payload.get("emitted_work_item_ids", [])],
        )


@dataclass(frozen=True)
class AuditWorkflowIntakeResult:
    schema_version: str
    created_work_items: List[AuditWorkflowWorkItem] = field(default_factory=list)
    workflow_index: Optional[AuditWorkflowIndex] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "created_work_items": [item.to_dict() for item in self.created_work_items],
            "workflow_index": self.workflow_index.to_dict() if self.workflow_index is not None else None,
        }


def load_audit_workflow_intake_state(path: Path) -> AuditWorkflowIntakeState:
    if not path.exists():
        return AuditWorkflowIntakeState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AuditWorkflowIntakeState.from_dict(payload)


def save_audit_workflow_intake_state(path: Path, state: AuditWorkflowIntakeState) -> None:
    _write_json(path, state.to_dict())


def load_materialized_audit_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["audit_id"]))
    return rows


def load_existing_work_items(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))
    return rows


def _work_item_id_from_record(record: Dict[str, object]) -> str:
    return str(record["audit_id"])


def _build_work_item(record: Dict[str, object]) -> AuditWorkflowWorkItem:
    payload = {
        "work_item_id": str(record["audit_id"]),
        "audit_id": str(record["audit_id"]),
        "tenant_id": str(record["tenant_id"]),
        "audit_kind": str(record["audit_kind"]),
        "schedule_id": str(record["schedule_id"]),
        "due_date": str(record["due_date"]),
        "creation_date": str(record["creation_date"]),
        "workflow_origin": str(record["workflow_origin"]),
        "source_request_id": str(record["source_request_id"]),
        "source_queue_id": str(record["source_queue_id"]),
        "intake_status": "READY_FOR_AUDIT_EXECUTION",
        "execution_status": "NOT_STARTED",
        "release_ready": bool(record.get("release_ready", False)),
    }
    return AuditWorkflowWorkItem(
        work_item_id=payload["work_item_id"],
        audit_id=payload["audit_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        due_date=payload["due_date"],
        creation_date=payload["creation_date"],
        workflow_origin=payload["workflow_origin"],
        source_request_id=payload["source_request_id"],
        source_queue_id=payload["source_queue_id"],
        intake_status=payload["intake_status"],
        execution_status=payload["execution_status"],
        release_ready=payload["release_ready"],
        payload_hash=_stable_json_hash(payload),
    )


def _count_by_key(rows: List[Dict[str, object]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        counts[str(row[key])] = counts.get(str(row[key]), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def build_audit_workflow_intake_outputs(
    *,
    materialized_audit_records: List[Dict[str, object]],
    existing_work_items: Optional[List[Dict[str, object]]] = None,
    state: Optional[AuditWorkflowIntakeState] = None,
) -> Tuple[AuditWorkflowIntakeResult, AuditWorkflowIntakeState]:
    current_state = state or AuditWorkflowIntakeState()
    existing_rows = existing_work_items or []

    emitted_work_item_ids: Set[str] = set(current_state.emitted_work_item_ids)
    existing_work_ids: Set[str] = {str(row["work_item_id"]) for row in existing_rows}

    created_work_items: List[AuditWorkflowWorkItem] = []

    for record in materialized_audit_records:
        assert isinstance(record, dict)
        work_item_id = _work_item_id_from_record(record)
        if work_item_id in emitted_work_item_ids or work_item_id in existing_work_ids:
            emitted_work_item_ids.add(work_item_id)
            existing_work_ids.add(work_item_id)
            continue
        work_item = _build_work_item(record)
        created_work_items.append(work_item)
        emitted_work_item_ids.add(work_item_id)
        existing_work_ids.add(work_item_id)

    created_work_items.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date, item.work_item_id))

    combined_rows: List[Dict[str, object]] = list(existing_rows) + [item.to_dict() for item in created_work_items]
    combined_rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))

    total_open_work_items = sum(1 for row in combined_rows if str(row.get("execution_status")) != "COMPLETED")
    total_release_ready = sum(1 for row in combined_rows if bool(row.get("release_ready", False)))

    index_payload = {
        "schema_version": AUDIT_WORKFLOW_INTAKE_SCHEMA_VERSION,
        "total_records_seen": len(materialized_audit_records),
        "total_new_work_items": len(created_work_items),
        "total_existing_work_items": len(combined_rows),
        "total_open_work_items": total_open_work_items,
        "total_release_ready": total_release_ready,
        "tenant_counts": _count_by_key(combined_rows, "tenant_id"),
        "audit_kind_counts": _count_by_key(combined_rows, "audit_kind"),
    }
    workflow_index = AuditWorkflowIndex(
        schema_version=index_payload["schema_version"],
        total_records_seen=index_payload["total_records_seen"],
        total_new_work_items=index_payload["total_new_work_items"],
        total_existing_work_items=index_payload["total_existing_work_items"],
        total_open_work_items=index_payload["total_open_work_items"],
        total_release_ready=index_payload["total_release_ready"],
        tenant_counts=index_payload["tenant_counts"],
        audit_kind_counts=index_payload["audit_kind_counts"],
        payload_hash=_stable_json_hash(index_payload),
    )

    result = AuditWorkflowIntakeResult(
        schema_version=AUDIT_WORKFLOW_INTAKE_SCHEMA_VERSION,
        created_work_items=created_work_items,
        workflow_index=workflow_index,
    )
    next_state = AuditWorkflowIntakeState(
        emitted_work_item_ids=sorted(emitted_work_item_ids),
    )
    return result, next_state


def append_audit_workflow_work_items(
    *,
    work_items: List[AuditWorkflowWorkItem],
    path: Path,
) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["work_item_id"]) for row in existing}

    for work_item in work_items:
        row = work_item.to_dict()
        if row["work_item_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["work_item_id"]))

    existing.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))
    _write_jsonl(path, existing)


def write_audit_workflow_index(path: Path, workflow_index: AuditWorkflowIndex) -> None:
    _write_json(path, workflow_index.to_dict())
