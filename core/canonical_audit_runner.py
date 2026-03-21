from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


CANONICAL_AUDIT_RUNNER_SCHEMA_VERSION = "1.0"


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
class AuditRunJob:
    job_id: str
    audit_id: str
    work_item_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: str
    due_date: str
    creation_date: str
    intake_status: str
    execution_status: str
    run_status: str
    source_work_item_id: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditRunnerIndex:
    schema_version: str
    total_work_items_seen: int
    total_new_jobs: int
    total_existing_jobs: int
    total_open_jobs: int
    total_completed_jobs: int
    tenant_counts: Dict[str, int]
    audit_kind_counts: Dict[str, int]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditRunnerState:
    emitted_job_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {"emitted_job_ids": sorted(set(self.emitted_job_ids))}

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "AuditRunnerState":
        return cls(emitted_job_ids=[str(x) for x in payload.get("emitted_job_ids", [])])


@dataclass(frozen=True)
class AuditRunnerResult:
    schema_version: str
    created_jobs: List[AuditRunJob] = field(default_factory=list)
    runner_index: Optional[AuditRunnerIndex] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "created_jobs": [item.to_dict() for item in self.created_jobs],
            "runner_index": self.runner_index.to_dict() if self.runner_index is not None else None,
        }


def load_audit_runner_state(path: Path) -> AuditRunnerState:
    if not path.exists():
        return AuditRunnerState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AuditRunnerState.from_dict(payload)


def save_audit_runner_state(path: Path, state: AuditRunnerState) -> None:
    _write_json(path, state.to_dict())


def load_work_items(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["work_item_id"]))
    return rows


def load_existing_jobs(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    return rows


def _job_id_from_work_item(work_item: Dict[str, object]) -> str:
    return str(work_item["work_item_id"])


def _build_job(work_item: Dict[str, object]) -> AuditRunJob:
    payload = {
        "job_id": str(work_item["work_item_id"]),
        "audit_id": str(work_item["audit_id"]),
        "work_item_id": str(work_item["work_item_id"]),
        "tenant_id": str(work_item["tenant_id"]),
        "audit_kind": str(work_item["audit_kind"]),
        "schedule_id": str(work_item["schedule_id"]),
        "due_date": str(work_item["due_date"]),
        "creation_date": str(work_item["creation_date"]),
        "intake_status": str(work_item["intake_status"]),
        "execution_status": str(work_item["execution_status"]),
        "run_status": "QUEUED",
        "source_work_item_id": str(work_item["work_item_id"]),
    }
    return AuditRunJob(
        job_id=payload["job_id"],
        audit_id=payload["audit_id"],
        work_item_id=payload["work_item_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        due_date=payload["due_date"],
        creation_date=payload["creation_date"],
        intake_status=payload["intake_status"],
        execution_status=payload["execution_status"],
        run_status=payload["run_status"],
        source_work_item_id=payload["source_work_item_id"],
        payload_hash=_stable_json_hash(payload),
    )


def _count_by_key(rows: List[Dict[str, object]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def build_audit_runner_outputs(
    *,
    work_items: List[Dict[str, object]],
    existing_jobs: Optional[List[Dict[str, object]]] = None,
    state: Optional[AuditRunnerState] = None,
) -> Tuple[AuditRunnerResult, AuditRunnerState]:
    current_state = state or AuditRunnerState()
    existing_rows = existing_jobs or []

    emitted_job_ids: Set[str] = set(current_state.emitted_job_ids)
    existing_job_ids: Set[str] = {str(row["job_id"]) for row in existing_rows}

    created_jobs: List[AuditRunJob] = []

    for work_item in work_items:
        assert isinstance(work_item, dict)
        job_id = _job_id_from_work_item(work_item)
        if job_id in emitted_job_ids or job_id in existing_job_ids:
            emitted_job_ids.add(job_id)
            existing_job_ids.add(job_id)
            continue
        if str(work_item.get("intake_status")) != "READY_FOR_AUDIT_EXECUTION":
            continue
        created_job = _build_job(work_item)
        created_jobs.append(created_job)
        emitted_job_ids.add(job_id)
        existing_job_ids.add(job_id)

    created_jobs.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.schedule_id, item.due_date, item.job_id))

    combined_rows: List[Dict[str, object]] = list(existing_rows) + [job.to_dict() for job in created_jobs]
    combined_rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))

    total_open_jobs = sum(1 for row in combined_rows if str(row.get("run_status")) != "COMPLETED")
    total_completed_jobs = sum(1 for row in combined_rows if str(row.get("run_status")) == "COMPLETED")

    index_payload = {
        "schema_version": CANONICAL_AUDIT_RUNNER_SCHEMA_VERSION,
        "total_work_items_seen": len(work_items),
        "total_new_jobs": len(created_jobs),
        "total_existing_jobs": len(combined_rows),
        "total_open_jobs": total_open_jobs,
        "total_completed_jobs": total_completed_jobs,
        "tenant_counts": _count_by_key(combined_rows, "tenant_id"),
        "audit_kind_counts": _count_by_key(combined_rows, "audit_kind"),
    }
    runner_index = AuditRunnerIndex(
        schema_version=index_payload["schema_version"],
        total_work_items_seen=index_payload["total_work_items_seen"],
        total_new_jobs=index_payload["total_new_jobs"],
        total_existing_jobs=index_payload["total_existing_jobs"],
        total_open_jobs=index_payload["total_open_jobs"],
        total_completed_jobs=index_payload["total_completed_jobs"],
        tenant_counts=index_payload["tenant_counts"],
        audit_kind_counts=index_payload["audit_kind_counts"],
        payload_hash=_stable_json_hash(index_payload),
    )

    result = AuditRunnerResult(
        schema_version=CANONICAL_AUDIT_RUNNER_SCHEMA_VERSION,
        created_jobs=created_jobs,
        runner_index=runner_index,
    )
    next_state = AuditRunnerState(emitted_job_ids=sorted(emitted_job_ids))
    return result, next_state


def append_jobs(*, jobs: List[AuditRunJob], path: Path) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["job_id"]) for row in existing}

    for job in jobs:
        row = job.to_dict()
        if row["job_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["job_id"]))

    existing.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["job_id"]))
    _write_jsonl(path, existing)


def write_runner_index(path: Path, runner_index: AuditRunnerIndex) -> None:
    _write_json(path, runner_index.to_dict())
