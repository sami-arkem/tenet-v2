from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


REMEDIATION_LIFECYCLE_SCHEMA_VERSION = "1.0"

VALID_STATUSES = {
    "OPEN",
    "IN_PROGRESS",
    "EVIDENCE_SUBMITTED",
    "VERIFYING",
    "CLOSED",
}

VALID_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS"},
    "IN_PROGRESS": {"EVIDENCE_SUBMITTED", "OPEN"},
    "EVIDENCE_SUBMITTED": {"IN_PROGRESS"},
    "VERIFYING": set(),
    "CLOSED": {"OPEN"},
}


def _utc_now_iso() -> str:
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


def _write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")


@dataclass(frozen=True)
class RemediationTimelineEvent:
    event_id: str
    remediation_id: str
    tenant_id: str
    audit_id: str
    actor_type: str
    actor_id: str
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    note: str
    evidence_file_ids: List[str]
    created_at: str
    immutable: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationLifecycleRecord:
    remediation_id: str
    audit_id: str
    job_id: str
    tenant_id: str
    audit_kind: str
    source_type: str
    source_key: str
    severity: str
    title: str
    detail: str
    status: str
    owner_user_id: Optional[str]
    due_date: Optional[str]
    evidence_file_ids: List[str]
    release_blocking: bool
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationLifecycleIndex:
    schema_version: str
    total_items: int
    total_open: int
    total_in_progress: int
    total_evidence_submitted: int
    total_verifying: int
    total_closed: int
    total_overdue: int
    total_due_in_7_days: int
    total_release_blocking_open: int
    owner_counts: Dict[str, int]
    severity_counts: Dict[str, int]
    tenant_counts: Dict[str, int]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationLifecycleGate:
    schema_version: str
    gate_name: str
    gate_status: str
    remediation_ready: bool
    unresolved_release_blockers: List[str]
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_lifecycle_items(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))
    return rows


def load_timeline(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"]))
    return rows


def load_gate(path: Path) -> Dict[str, object]:
    return _read_json(path)


def write_lifecycle_items(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))
    _write_jsonl(path, rows)


def write_timeline(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"]))
    _write_jsonl(path, rows)


def write_lifecycle_index(path: Path, artifact: RemediationLifecycleIndex) -> None:
    _write_json(path, artifact.to_dict())


def write_lifecycle_gate(path: Path, artifact: RemediationLifecycleGate) -> None:
    _write_json(path, artifact.to_dict())


def _count_by(rows: List[Dict[str, object]], key: str, default: str = "UNASSIGNED") -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        normalized = str(value) if value not in (None, "") else default
        counts[normalized] = counts.get(normalized, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _is_overdue(row: Dict[str, object], today: str) -> bool:
    due_date = row.get("due_date")
    status = str(row.get("status"))
    return bool(due_date) and str(due_date) < today and status != "CLOSED"


def _is_due_in_7_days(row: Dict[str, object], today: str) -> bool:
    due_date = row.get("due_date")
    status = str(row.get("status"))
    if not due_date or status == "CLOSED":
        return False
    try:
        due_dt = datetime.strptime(str(due_date), "%Y-%m-%d").date()
        today_dt = datetime.strptime(today, "%Y-%m-%d").date()
    except ValueError:
        return False
    delta = (due_dt - today_dt).days
    return 0 <= delta <= 7


def recompute_lifecycle_artifacts(
    *,
    lifecycle_items: List[Dict[str, object]],
    today: Optional[str] = None,
) -> Tuple[RemediationLifecycleIndex, RemediationLifecycleGate]:
    today_value = today or datetime.now(timezone.utc).date().isoformat()

    total_items = len(lifecycle_items)
    total_open = sum(1 for row in lifecycle_items if str(row.get("status")) == "OPEN")
    total_in_progress = sum(1 for row in lifecycle_items if str(row.get("status")) == "IN_PROGRESS")
    total_evidence_submitted = sum(1 for row in lifecycle_items if str(row.get("status")) == "EVIDENCE_SUBMITTED")
    total_verifying = sum(1 for row in lifecycle_items if str(row.get("status")) == "VERIFYING")
    total_closed = sum(1 for row in lifecycle_items if str(row.get("status")) == "CLOSED")
    total_overdue = sum(1 for row in lifecycle_items if _is_overdue(row, today_value))
    total_due_in_7_days = sum(1 for row in lifecycle_items if _is_due_in_7_days(row, today_value))
    unresolved_release_blockers = sorted(
        row["remediation_id"]
        for row in lifecycle_items
        if bool(row.get("release_blocking", False)) and str(row.get("status")) != "CLOSED"
    )
    total_release_blocking_open = len(unresolved_release_blockers)

    index_payload = {
        "schema_version": REMEDIATION_LIFECYCLE_SCHEMA_VERSION,
        "total_items": total_items,
        "total_open": total_open,
        "total_in_progress": total_in_progress,
        "total_evidence_submitted": total_evidence_submitted,
        "total_verifying": total_verifying,
        "total_closed": total_closed,
        "total_overdue": total_overdue,
        "total_due_in_7_days": total_due_in_7_days,
        "total_release_blocking_open": total_release_blocking_open,
        "owner_counts": _count_by(lifecycle_items, "owner_user_id"),
        "severity_counts": _count_by(lifecycle_items, "severity", default="UNKNOWN"),
        "tenant_counts": _count_by(lifecycle_items, "tenant_id", default="UNKNOWN"),
    }
    index_artifact = RemediationLifecycleIndex(
        schema_version=index_payload["schema_version"],
        total_items=index_payload["total_items"],
        total_open=index_payload["total_open"],
        total_in_progress=index_payload["total_in_progress"],
        total_evidence_submitted=index_payload["total_evidence_submitted"],
        total_verifying=index_payload["total_verifying"],
        total_closed=index_payload["total_closed"],
        total_overdue=index_payload["total_overdue"],
        total_due_in_7_days=index_payload["total_due_in_7_days"],
        total_release_blocking_open=index_payload["total_release_blocking_open"],
        owner_counts=index_payload["owner_counts"],
        severity_counts=index_payload["severity_counts"],
        tenant_counts=index_payload["tenant_counts"],
        payload_hash=_stable_json_hash(index_payload),
    )

    blocking_reasons = [f"remediation:unresolved_release_blockers:{len(unresolved_release_blockers)}"] if unresolved_release_blockers else []
    gate_payload = {
        "schema_version": REMEDIATION_LIFECYCLE_SCHEMA_VERSION,
        "gate_name": "remediation_tracking_gate",
        "gate_status": "PASS" if not unresolved_release_blockers else "BLOCKED",
        "remediation_ready": not unresolved_release_blockers,
        "unresolved_release_blockers": unresolved_release_blockers,
        "blocking_reasons": blocking_reasons,
    }
    gate_artifact = RemediationLifecycleGate(
        schema_version=gate_payload["schema_version"],
        gate_name=gate_payload["gate_name"],
        gate_status=gate_payload["gate_status"],
        remediation_ready=gate_payload["remediation_ready"],
        unresolved_release_blockers=gate_payload["unresolved_release_blockers"],
        blocking_reasons=gate_payload["blocking_reasons"],
        payload_hash=_stable_json_hash(gate_payload),
    )

    return index_artifact, gate_artifact


def initialize_lifecycle_items(base_items: List[Dict[str, object]], *, now: Optional[str] = None) -> List[Dict[str, object]]:
    now_value = now or _utc_now_iso()
    initialized: List[Dict[str, object]] = []
    for row in base_items:
        payload = {
            "remediation_id": str(row["remediation_id"]),
            "audit_id": str(row["audit_id"]),
            "job_id": str(row["job_id"]),
            "tenant_id": str(row["tenant_id"]),
            "audit_kind": str(row["audit_kind"]),
            "source_type": str(row["source_type"]),
            "source_key": str(row["source_key"]),
            "severity": str(row["severity"]),
            "title": str(row["title"]),
            "detail": str(row["detail"]),
            "status": str(row.get("status", "OPEN")),
            "owner_user_id": row.get("owner_user_id"),
            "due_date": row.get("due_date"),
            "evidence_file_ids": list(row.get("evidence_file_ids", [])),
            "release_blocking": bool(row.get("release_blocking", False)),
            "created_at": str(row.get("created_at") or now_value),
            "updated_at": str(row.get("updated_at") or now_value),
            "closed_at": row.get("closed_at"),
        }
        initialized.append(
            RemediationLifecycleRecord(
                remediation_id=payload["remediation_id"],
                audit_id=payload["audit_id"],
                job_id=payload["job_id"],
                tenant_id=payload["tenant_id"],
                audit_kind=payload["audit_kind"],
                source_type=payload["source_type"],
                source_key=payload["source_key"],
                severity=payload["severity"],
                title=payload["title"],
                detail=payload["detail"],
                status=payload["status"],
                owner_user_id=payload["owner_user_id"],
                due_date=payload["due_date"],
                evidence_file_ids=payload["evidence_file_ids"],
                release_blocking=payload["release_blocking"],
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
                closed_at=payload["closed_at"],
                payload_hash=_stable_json_hash(payload),
            ).to_dict()
        )
    initialized.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))
    return initialized


def initialize_timeline(lifecycle_items: List[Dict[str, object]], *, now: Optional[str] = None) -> List[Dict[str, object]]:
    now_value = now or _utc_now_iso()
    rows: List[Dict[str, object]] = []
    for item in lifecycle_items:
        payload = {
            "event_id": f"{item['remediation_id']}:created",
            "remediation_id": str(item["remediation_id"]),
            "tenant_id": str(item["tenant_id"]),
            "audit_id": str(item["audit_id"]),
            "actor_type": "SYSTEM",
            "actor_id": "tenet",
            "action": "CREATED",
            "from_status": None,
            "to_status": str(item["status"]),
            "note": "Remediation item created by Tenet from deterministic audit output.",
            "evidence_file_ids": list(item.get("evidence_file_ids", [])),
            "created_at": now_value,
            "immutable": True,
        }
        rows.append(
            RemediationTimelineEvent(
                event_id=payload["event_id"],
                remediation_id=payload["remediation_id"],
                tenant_id=payload["tenant_id"],
                audit_id=payload["audit_id"],
                actor_type=payload["actor_type"],
                actor_id=payload["actor_id"],
                action=payload["action"],
                from_status=payload["from_status"],
                to_status=payload["to_status"],
                note=payload["note"],
                evidence_file_ids=payload["evidence_file_ids"],
                created_at=payload["created_at"],
                immutable=payload["immutable"],
                payload_hash=_stable_json_hash(payload),
            ).to_dict()
        )
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"]))
    return rows


def assign_owner(
    *,
    lifecycle_items: List[Dict[str, object]],
    timeline: List[Dict[str, object]],
    remediation_id: str,
    owner_user_id: str,
    actor_user_id: str,
    note: str,
    now: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    if len(note.strip()) < 10:
        raise ValueError("Please add a note explaining this owner assignment")

    now_value = now or _utc_now_iso()
    found = False
    updated_items: List[Dict[str, object]] = []

    for row in lifecycle_items:
        row = dict(row)
        if str(row["remediation_id"]) == remediation_id:
            found = True
            row["owner_user_id"] = owner_user_id
            row["updated_at"] = now_value
            row["payload_hash"] = _stable_json_hash({
                "remediation_id": row["remediation_id"],
                "audit_id": row["audit_id"],
                "job_id": row["job_id"],
                "tenant_id": row["tenant_id"],
                "audit_kind": row["audit_kind"],
                "source_type": row["source_type"],
                "source_key": row["source_key"],
                "severity": row["severity"],
                "title": row["title"],
                "detail": row["detail"],
                "status": row["status"],
                "owner_user_id": row["owner_user_id"],
                "due_date": row["due_date"],
                "evidence_file_ids": row["evidence_file_ids"],
                "release_blocking": row["release_blocking"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "closed_at": row["closed_at"],
            })
        updated_items.append(row)

    if not found:
        raise ValueError(f"Remediation item not found: {remediation_id}")

    event_payload = {
        "event_id": f"{remediation_id}:assign:{now_value}:{actor_user_id}",
        "remediation_id": remediation_id,
        "tenant_id": next(row["tenant_id"] for row in updated_items if row["remediation_id"] == remediation_id),
        "audit_id": next(row["audit_id"] for row in updated_items if row["remediation_id"] == remediation_id),
        "actor_type": "USER",
        "actor_id": actor_user_id,
        "action": "OWNER_ASSIGNED",
        "from_status": None,
        "to_status": None,
        "note": note.strip(),
        "evidence_file_ids": [],
        "created_at": now_value,
        "immutable": True,
    }
    updated_timeline = list(timeline) + [
        RemediationTimelineEvent(
            event_id=event_payload["event_id"],
            remediation_id=event_payload["remediation_id"],
            tenant_id=event_payload["tenant_id"],
            audit_id=event_payload["audit_id"],
            actor_type=event_payload["actor_type"],
            actor_id=event_payload["actor_id"],
            action=event_payload["action"],
            from_status=event_payload["from_status"],
            to_status=event_payload["to_status"],
            note=event_payload["note"],
            evidence_file_ids=event_payload["evidence_file_ids"],
            created_at=event_payload["created_at"],
            immutable=event_payload["immutable"],
            payload_hash=_stable_json_hash(event_payload),
        ).to_dict()
    ]

    return (
        sorted(updated_items, key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"])),
        sorted(updated_timeline, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"])),
    )


def transition_status(
    *,
    lifecycle_items: List[Dict[str, object]],
    timeline: List[Dict[str, object]],
    remediation_id: str,
    to_status: str,
    actor_user_id: str,
    note: str,
    evidence_file_ids: Optional[List[str]] = None,
    now: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    if to_status not in VALID_STATUSES:
        raise ValueError(f"Invalid remediation status: {to_status}")
    if len(note.strip()) < 10:
        raise ValueError("Please add a note explaining this status change")

    now_value = now or _utc_now_iso()
    evidence_ids = sorted(dict.fromkeys(evidence_file_ids or []))
    found = False
    updated_items: List[Dict[str, object]] = []
    current_row: Optional[Dict[str, object]] = None

    for row in lifecycle_items:
        row = dict(row)
        if str(row["remediation_id"]) == remediation_id:
            found = True
            current_row = row
            from_status = str(row["status"])
            allowed = VALID_TRANSITIONS.get(from_status, set())
            if to_status not in allowed:
                raise ValueError(f"Invalid status transition: {from_status} -> {to_status}")
            if to_status == "EVIDENCE_SUBMITTED" and not evidence_ids:
                raise ValueError("Please attach remediation evidence")

            row["status"] = to_status
            row["updated_at"] = now_value

            if to_status == "EVIDENCE_SUBMITTED":
                row["evidence_file_ids"] = evidence_ids
            if to_status == "CLOSED":
                row["closed_at"] = now_value
            elif to_status != "CLOSED":
                row["closed_at"] = None

            row["payload_hash"] = _stable_json_hash({
                "remediation_id": row["remediation_id"],
                "audit_id": row["audit_id"],
                "job_id": row["job_id"],
                "tenant_id": row["tenant_id"],
                "audit_kind": row["audit_kind"],
                "source_type": row["source_type"],
                "source_key": row["source_key"],
                "severity": row["severity"],
                "title": row["title"],
                "detail": row["detail"],
                "status": row["status"],
                "owner_user_id": row["owner_user_id"],
                "due_date": row["due_date"],
                "evidence_file_ids": row["evidence_file_ids"],
                "release_blocking": row["release_blocking"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "closed_at": row["closed_at"],
            })
        updated_items.append(row)

    if not found or current_row is None:
        raise ValueError(f"Remediation item not found: {remediation_id}")

    event_payload = {
        "event_id": f"{remediation_id}:transition:{now_value}:{actor_user_id}:{to_status}",
        "remediation_id": remediation_id,
        "tenant_id": str(current_row["tenant_id"]),
        "audit_id": str(current_row["audit_id"]),
        "actor_type": "USER",
        "actor_id": actor_user_id,
        "action": "STATUS_CHANGED",
        "from_status": str(current_row["status"]),
        "to_status": to_status,
        "note": note.strip(),
        "evidence_file_ids": evidence_ids,
        "created_at": now_value,
        "immutable": True,
    }
    updated_timeline = list(timeline) + [
        RemediationTimelineEvent(
            event_id=event_payload["event_id"],
            remediation_id=event_payload["remediation_id"],
            tenant_id=event_payload["tenant_id"],
            audit_id=event_payload["audit_id"],
            actor_type=event_payload["actor_type"],
            actor_id=event_payload["actor_id"],
            action=event_payload["action"],
            from_status=event_payload["from_status"],
            to_status=event_payload["to_status"],
            note=event_payload["note"],
            evidence_file_ids=event_payload["evidence_file_ids"],
            created_at=event_payload["created_at"],
            immutable=event_payload["immutable"],
            payload_hash=_stable_json_hash(event_payload),
        ).to_dict()
    ]

    return (
        sorted(updated_items, key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"])),
        sorted(updated_timeline, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"])),
    )


def submit_for_verification(
    *,
    lifecycle_items: List[Dict[str, object]],
    timeline: List[Dict[str, object]],
    remediation_id: str,
    actor_user_id: str,
    note: str,
    evidence_file_ids: List[str],
    now: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    items_after_submit, timeline_after_submit = transition_status(
        lifecycle_items=lifecycle_items,
        timeline=timeline,
        remediation_id=remediation_id,
        to_status="EVIDENCE_SUBMITTED",
        actor_user_id=actor_user_id,
        note=note,
        evidence_file_ids=evidence_file_ids,
        now=now,
    )

    now_value = now or _utc_now_iso()
    updated_items: List[Dict[str, object]] = []
    current_row: Optional[Dict[str, object]] = None

    for row in items_after_submit:
        row = dict(row)
        if str(row["remediation_id"]) == remediation_id:
            current_row = row
            row["status"] = "VERIFYING"
            row["updated_at"] = now_value
            row["payload_hash"] = _stable_json_hash({
                "remediation_id": row["remediation_id"],
                "audit_id": row["audit_id"],
                "job_id": row["job_id"],
                "tenant_id": row["tenant_id"],
                "audit_kind": row["audit_kind"],
                "source_type": row["source_type"],
                "source_key": row["source_key"],
                "severity": row["severity"],
                "title": row["title"],
                "detail": row["detail"],
                "status": row["status"],
                "owner_user_id": row["owner_user_id"],
                "due_date": row["due_date"],
                "evidence_file_ids": row["evidence_file_ids"],
                "release_blocking": row["release_blocking"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "closed_at": row["closed_at"],
            })
        updated_items.append(row)

    if current_row is None:
        raise ValueError(f"Remediation item not found: {remediation_id}")

    event_payload = {
        "event_id": f"{remediation_id}:verification_queued:{now_value}",
        "remediation_id": remediation_id,
        "tenant_id": str(current_row["tenant_id"]),
        "audit_id": str(current_row["audit_id"]),
        "actor_type": "SYSTEM",
        "actor_id": "tenet",
        "action": "VERIFICATION_QUEUED",
        "from_status": "EVIDENCE_SUBMITTED",
        "to_status": "VERIFYING",
        "note": "Uploading triggers automatic re-verification by Tenet.",
        "evidence_file_ids": list(current_row.get("evidence_file_ids", [])),
        "created_at": now_value,
        "immutable": True,
    }
    updated_timeline = list(timeline_after_submit) + [
        RemediationTimelineEvent(
            event_id=event_payload["event_id"],
            remediation_id=event_payload["remediation_id"],
            tenant_id=event_payload["tenant_id"],
            audit_id=event_payload["audit_id"],
            actor_type=event_payload["actor_type"],
            actor_id=event_payload["actor_id"],
            action=event_payload["action"],
            from_status=event_payload["from_status"],
            to_status=event_payload["to_status"],
            note=event_payload["note"],
            evidence_file_ids=event_payload["evidence_file_ids"],
            created_at=event_payload["created_at"],
            immutable=event_payload["immutable"],
            payload_hash=_stable_json_hash(event_payload),
        ).to_dict()
    ]

    return (
        sorted(updated_items, key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"])),
        sorted(updated_timeline, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"])),
    )


def apply_verification_result(
    *,
    lifecycle_items: List[Dict[str, object]],
    timeline: List[Dict[str, object]],
    remediation_id: str,
    verification_passed: bool,
    updated_gap_note: Optional[str] = None,
    now: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    now_value = now or _utc_now_iso()
    found = False
    updated_items: List[Dict[str, object]] = []
    current_row: Optional[Dict[str, object]] = None

    for row in lifecycle_items:
        row = dict(row)
        if str(row["remediation_id"]) == remediation_id:
            found = True
            current_row = row
            if str(row["status"]) != "VERIFYING":
                raise ValueError("Verification result can only be applied from VERIFYING state")

            if verification_passed:
                row["status"] = "CLOSED"
                row["closed_at"] = now_value
            else:
                row["status"] = "IN_PROGRESS"
                row["closed_at"] = None
                if updated_gap_note:
                    row["detail"] = updated_gap_note

            row["updated_at"] = now_value
            row["payload_hash"] = _stable_json_hash({
                "remediation_id": row["remediation_id"],
                "audit_id": row["audit_id"],
                "job_id": row["job_id"],
                "tenant_id": row["tenant_id"],
                "audit_kind": row["audit_kind"],
                "source_type": row["source_type"],
                "source_key": row["source_key"],
                "severity": row["severity"],
                "title": row["title"],
                "detail": row["detail"],
                "status": row["status"],
                "owner_user_id": row["owner_user_id"],
                "due_date": row["due_date"],
                "evidence_file_ids": row["evidence_file_ids"],
                "release_blocking": row["release_blocking"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "closed_at": row["closed_at"],
            })
        updated_items.append(row)

    if not found or current_row is None:
        raise ValueError(f"Remediation item not found: {remediation_id}")

    event_payload = {
        "event_id": f"{remediation_id}:verification_result:{now_value}",
        "remediation_id": remediation_id,
        "tenant_id": str(current_row["tenant_id"]),
        "audit_id": str(current_row["audit_id"]),
        "actor_type": "SYSTEM",
        "actor_id": "tenet",
        "action": "VERIFICATION_RESULT",
        "from_status": "VERIFYING",
        "to_status": "CLOSED" if verification_passed else "IN_PROGRESS",
        "note": (
            "Finding closed — control now passes"
            if verification_passed
            else (updated_gap_note or "Verification failed — remediation returned to in-progress state")
        ),
        "evidence_file_ids": list(current_row.get("evidence_file_ids", [])),
        "created_at": now_value,
        "immutable": True,
    }
    updated_timeline = list(timeline) + [
        RemediationTimelineEvent(
            event_id=event_payload["event_id"],
            remediation_id=event_payload["remediation_id"],
            tenant_id=event_payload["tenant_id"],
            audit_id=event_payload["audit_id"],
            actor_type=event_payload["actor_type"],
            actor_id=event_payload["actor_id"],
            action=event_payload["action"],
            from_status=event_payload["from_status"],
            to_status=event_payload["to_status"],
            note=event_payload["note"],
            evidence_file_ids=event_payload["evidence_file_ids"],
            created_at=event_payload["created_at"],
            immutable=event_payload["immutable"],
            payload_hash=_stable_json_hash(event_payload),
        ).to_dict()
    ]

    return (
        sorted(updated_items, key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"])),
        sorted(updated_timeline, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"])),
    )
