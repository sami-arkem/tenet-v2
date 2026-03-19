from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from core.remediation_lifecycle import (
    assign_owner,
    apply_verification_result,
    initialize_lifecycle_items,
    initialize_timeline,
    load_gate,
    load_lifecycle_items,
    load_timeline,
    recompute_lifecycle_artifacts,
    submit_for_verification,
    transition_status,
    write_lifecycle_gate,
    write_lifecycle_index,
    write_lifecycle_items,
    write_timeline,
)


REMEDIATION_OPERATOR_SERVICE_SCHEMA_VERSION = "1.0"

VIEW_ROLES = {"ADMIN", "OWNER", "ANALYST", "VIEWER"}
MUTATION_ROLES = {"ADMIN", "OWNER", "ANALYST"}
OWNER_ASSIGNMENT_ROLES = {"ADMIN", "OWNER"}
VERIFICATION_ROLES = {"ADMIN", "OWNER", "ANALYST"}


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
class ActorContext:
    user_id: str
    tenant_id: str
    role: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceMetadataRecord:
    evidence_metadata_id: str
    remediation_id: str
    tenant_id: str
    audit_id: str
    uploaded_by_user_id: str
    file_id: str
    filename: str
    content_type: str
    sha256: str
    byte_size: int
    uploaded_at: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotificationOutboxEvent:
    event_id: str
    tenant_id: str
    remediation_id: str
    event_type: str
    recipient_user_ids: List[str]
    payload: Dict[str, object]
    created_at: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OperatorAuditLogEvent:
    audit_log_id: str
    tenant_id: str
    remediation_id: str
    actor_user_id: str
    actor_role: str
    action: str
    note: str
    created_at: str
    immutable: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationOperatorPaths:
    items: str
    timeline: str
    lifecycle_index: str
    gate: str
    evidence_metadata: str
    notification_outbox: str
    operator_audit_log: str


def load_actor_directory(path: Path) -> Dict[str, Dict[str, object]]:
    payload = _read_json(path)
    raw = payload.get("users", payload)
    if not isinstance(raw, dict):
        return {}
    normalized: Dict[str, Dict[str, object]] = {}
    for user_id, row in raw.items():
        if isinstance(row, dict):
            normalized[str(user_id)] = row
    return normalized


def load_evidence_metadata(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["remediation_id"], row["uploaded_at"], row["evidence_metadata_id"]))
    return rows


def load_notification_outbox(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["event_id"]))
    return rows


def load_operator_audit_log(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["audit_log_id"]))
    return rows


def write_evidence_metadata(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["remediation_id"], row["uploaded_at"], row["evidence_metadata_id"]))
    _write_jsonl(path, rows)


def write_notification_outbox(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["event_id"]))
    _write_jsonl(path, rows)


def write_operator_audit_log(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["audit_log_id"]))
    _write_jsonl(path, rows)


def require_actor(actor_directory: Dict[str, Dict[str, object]], actor_user_id: str) -> ActorContext:
    actor = actor_directory.get(actor_user_id)
    if actor is None:
        raise PermissionError("Authentication required")
    role = str(actor.get("role", "")).upper()
    tenant_id = str(actor.get("tenant_id", ""))
    if not tenant_id or role not in VIEW_ROLES:
        raise PermissionError("Authentication required")
    return ActorContext(
        user_id=actor_user_id,
        tenant_id=tenant_id,
        role=role,
    )


def _find_remediation(items: List[Dict[str, object]], remediation_id: str) -> Dict[str, object]:
    for row in items:
        if str(row["remediation_id"]) == remediation_id:
            return row
    raise ValueError(f"Remediation item not found: {remediation_id}")


def _require_same_tenant(actor: ActorContext, remediation: Dict[str, object]) -> None:
    if str(remediation["tenant_id"]) != actor.tenant_id:
        raise PermissionError("Forbidden")


def _require_role(actor: ActorContext, allowed_roles: set[str]) -> None:
    if actor.role not in allowed_roles:
        raise PermissionError("Forbidden")


def _require_owner_or_privileged(actor: ActorContext, remediation: Dict[str, object]) -> None:
    owner = remediation.get("owner_user_id")
    if actor.role in {"ADMIN", "OWNER"}:
        return
    if actor.role == "ANALYST" and str(owner or "") == actor.user_id:
        return
    raise PermissionError("Forbidden")


def _append_operator_audit_log(
    audit_log: List[Dict[str, object]],
    *,
    tenant_id: str,
    remediation_id: str,
    actor_user_id: str,
    actor_role: str,
    action: str,
    note: str,
    now: str,
) -> List[Dict[str, object]]:
    payload = {
        "audit_log_id": f"{remediation_id}:{action}:{now}:{actor_user_id}",
        "tenant_id": tenant_id,
        "remediation_id": remediation_id,
        "actor_user_id": actor_user_id,
        "actor_role": actor_role,
        "action": action,
        "note": note,
        "created_at": now,
        "immutable": True,
    }
    row = OperatorAuditLogEvent(
        audit_log_id=payload["audit_log_id"],
        tenant_id=payload["tenant_id"],
        remediation_id=payload["remediation_id"],
        actor_user_id=payload["actor_user_id"],
        actor_role=payload["actor_role"],
        action=payload["action"],
        note=payload["note"],
        created_at=payload["created_at"],
        immutable=payload["immutable"],
        payload_hash=_stable_json_hash(payload),
    ).to_dict()
    return sorted(
        list(audit_log) + [row],
        key=lambda item: (item["tenant_id"], item["created_at"], item["audit_log_id"]),
    )


def _append_notification(
    outbox: List[Dict[str, object]],
    *,
    tenant_id: str,
    remediation_id: str,
    event_type: str,
    recipient_user_ids: List[str],
    payload: Dict[str, object],
    now: str,
) -> List[Dict[str, object]]:
    row_payload = {
        "event_id": f"{remediation_id}:{event_type}:{now}",
        "tenant_id": tenant_id,
        "remediation_id": remediation_id,
        "event_type": event_type,
        "recipient_user_ids": sorted(dict.fromkeys(recipient_user_ids)),
        "payload": payload,
        "created_at": now,
    }
    row = NotificationOutboxEvent(
        event_id=row_payload["event_id"],
        tenant_id=row_payload["tenant_id"],
        remediation_id=row_payload["remediation_id"],
        event_type=row_payload["event_type"],
        recipient_user_ids=row_payload["recipient_user_ids"],
        payload=row_payload["payload"],
        created_at=row_payload["created_at"],
        payload_hash=_stable_json_hash(row_payload),
    ).to_dict()
    return sorted(
        list(outbox) + [row],
        key=lambda item: (item["tenant_id"], item["created_at"], item["event_id"]),
    )


def _append_evidence_metadata(
    evidence_rows: List[Dict[str, object]],
    *,
    remediation_id: str,
    tenant_id: str,
    audit_id: str,
    uploaded_by_user_id: str,
    file_id: str,
    filename: str,
    content_type: str,
    sha256: str,
    byte_size: int,
    now: str,
) -> List[Dict[str, object]]:
    payload = {
        "evidence_metadata_id": f"{remediation_id}:{file_id}",
        "remediation_id": remediation_id,
        "tenant_id": tenant_id,
        "audit_id": audit_id,
        "uploaded_by_user_id": uploaded_by_user_id,
        "file_id": file_id,
        "filename": filename,
        "content_type": content_type,
        "sha256": sha256,
        "byte_size": byte_size,
        "uploaded_at": now,
    }
    row = EvidenceMetadataRecord(
        evidence_metadata_id=payload["evidence_metadata_id"],
        remediation_id=payload["remediation_id"],
        tenant_id=payload["tenant_id"],
        audit_id=payload["audit_id"],
        uploaded_by_user_id=payload["uploaded_by_user_id"],
        file_id=payload["file_id"],
        filename=payload["filename"],
        content_type=payload["content_type"],
        sha256=payload["sha256"],
        byte_size=payload["byte_size"],
        uploaded_at=payload["uploaded_at"],
        payload_hash=_stable_json_hash(payload),
    ).to_dict()

    deduped = [existing for existing in evidence_rows if str(existing["evidence_metadata_id"]) != row["evidence_metadata_id"]]
    deduped.append(row)
    return sorted(
        deduped,
        key=lambda item: (item["tenant_id"], item["remediation_id"], item["uploaded_at"], item["evidence_metadata_id"]),
    )


def bootstrap_from_generated_remediation(
    *,
    generated_items_path: Path,
    operator_paths: RemediationOperatorPaths,
    now: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, object]:
    base_items = _read_jsonl(generated_items_path)
    lifecycle_items = initialize_lifecycle_items(base_items, now=now)
    timeline = initialize_timeline(lifecycle_items, now=now)
    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=lifecycle_items, today=today)

    write_lifecycle_items(Path(operator_paths.items), lifecycle_items)
    write_timeline(Path(operator_paths.timeline), timeline)
    write_lifecycle_index(Path(operator_paths.lifecycle_index), index_artifact)
    write_lifecycle_gate(Path(operator_paths.gate), gate_artifact)
    write_evidence_metadata(Path(operator_paths.evidence_metadata), [])
    write_notification_outbox(Path(operator_paths.notification_outbox), [])
    write_operator_audit_log(Path(operator_paths.operator_audit_log), [])

    return {
        "items": len(lifecycle_items),
        "timeline_events": len(timeline),
        "gate_status": gate_artifact.gate_status,
    }


def list_remediations(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    items_path: Path,
) -> List[Dict[str, object]]:
    actor = require_actor(actor_directory, actor_user_id)
    items = load_lifecycle_items(items_path)
    return [row for row in items if str(row["tenant_id"]) == actor.tenant_id]


def get_remediation_detail(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    remediation_id: str,
    items_path: Path,
    timeline_path: Path,
    evidence_metadata_path: Path,
) -> Dict[str, object]:
    actor = require_actor(actor_directory, actor_user_id)
    items = load_lifecycle_items(items_path)
    remediation = _find_remediation(items, remediation_id)
    _require_same_tenant(actor, remediation)

    timeline = [row for row in load_timeline(timeline_path) if str(row["remediation_id"]) == remediation_id]
    evidence_rows = [row for row in load_evidence_metadata(evidence_metadata_path) if str(row["remediation_id"]) == remediation_id]

    return {
        "remediation": remediation,
        "timeline": timeline,
        "evidence_metadata": evidence_rows,
    }


def assign_owner_api(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    remediation_id: str,
    owner_user_id: str,
    note: str,
    operator_paths: RemediationOperatorPaths,
    now: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, object]:
    actor = require_actor(actor_directory, actor_user_id)
    _require_role(actor, OWNER_ASSIGNMENT_ROLES)

    owner_actor = require_actor(actor_directory, owner_user_id)

    items = load_lifecycle_items(Path(operator_paths.items))
    timeline = load_timeline(Path(operator_paths.timeline))
    remediation = _find_remediation(items, remediation_id)
    _require_same_tenant(actor, remediation)

    if owner_actor.tenant_id != actor.tenant_id or owner_actor.role not in MUTATION_ROLES:
        raise PermissionError("Forbidden")

    audit_log = load_operator_audit_log(Path(operator_paths.operator_audit_log))
    outbox = load_notification_outbox(Path(operator_paths.notification_outbox))

    now_value = now or _utc_now_iso()

    updated_items, updated_timeline = assign_owner(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=remediation_id,
        owner_user_id=owner_user_id,
        actor_user_id=actor.user_id,
        note=note,
        now=now_value,
    )
    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items, today=today)

    audit_log = _append_operator_audit_log(
        audit_log,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        action="OWNER_ASSIGNED",
        note=note,
        now=now_value,
    )
    outbox = _append_notification(
        outbox,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        event_type="REMEDIATION_OWNER_ASSIGNED",
        recipient_user_ids=[owner_user_id],
        payload={"owner_user_id": owner_user_id, "remediation_id": remediation_id},
        now=now_value,
    )

    write_lifecycle_items(Path(operator_paths.items), updated_items)
    write_timeline(Path(operator_paths.timeline), updated_timeline)
    write_lifecycle_index(Path(operator_paths.lifecycle_index), index_artifact)
    write_lifecycle_gate(Path(operator_paths.gate), gate_artifact)
    write_operator_audit_log(Path(operator_paths.operator_audit_log), audit_log)
    write_notification_outbox(Path(operator_paths.notification_outbox), outbox)

    return {
        "remediation_id": remediation_id,
        "owner_user_id": owner_user_id,
        "gate_status": gate_artifact.gate_status,
    }


def set_due_date_api(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    remediation_id: str,
    due_date: str,
    note: str,
    operator_paths: RemediationOperatorPaths,
    now: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, object]:
    actor = require_actor(actor_directory, actor_user_id)
    _require_role(actor, OWNER_ASSIGNMENT_ROLES)

    items = load_lifecycle_items(Path(operator_paths.items))
    remediation = _find_remediation(items, remediation_id)
    _require_same_tenant(actor, remediation)

    if len(note.strip()) < 10:
        raise ValueError("Please add a note explaining this due date change")

    now_value = now or _utc_now_iso()
    updated_items: List[Dict[str, object]] = []

    for row in items:
        row = dict(row)
        if str(row["remediation_id"]) == remediation_id:
            row["due_date"] = due_date
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

    timeline = load_timeline(Path(operator_paths.timeline))
    audit_log = load_operator_audit_log(Path(operator_paths.operator_audit_log))
    outbox = load_notification_outbox(Path(operator_paths.notification_outbox))

    event_payload = {
        "event_id": f"{remediation_id}:due_date:{now_value}",
        "remediation_id": remediation_id,
        "tenant_id": actor.tenant_id,
        "audit_id": remediation["audit_id"],
        "actor_type": "USER",
        "actor_id": actor.user_id,
        "action": "DUE_DATE_SET",
        "from_status": None,
        "to_status": None,
        "note": note.strip(),
        "evidence_file_ids": [],
        "created_at": now_value,
        "immutable": True,
    }
    timeline = list(timeline) + [{
        **event_payload,
        "payload_hash": _stable_json_hash(event_payload),
    }]
    timeline = sorted(timeline, key=lambda row: (row["tenant_id"], row["audit_id"], row["remediation_id"], row["created_at"], row["event_id"]))

    audit_log = _append_operator_audit_log(
        audit_log,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        action="DUE_DATE_SET",
        note=note.strip(),
        now=now_value,
    )
    recipients = [str(remediation["owner_user_id"])] if remediation.get("owner_user_id") else [actor.user_id]
    outbox = _append_notification(
        outbox,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        event_type="REMEDIATION_DUE_DATE_SET",
        recipient_user_ids=recipients,
        payload={"due_date": due_date, "remediation_id": remediation_id},
        now=now_value,
    )

    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items, today=today)

    write_lifecycle_items(Path(operator_paths.items), updated_items)
    write_timeline(Path(operator_paths.timeline), timeline)
    write_lifecycle_index(Path(operator_paths.lifecycle_index), index_artifact)
    write_lifecycle_gate(Path(operator_paths.gate), gate_artifact)
    write_operator_audit_log(Path(operator_paths.operator_audit_log), audit_log)
    write_notification_outbox(Path(operator_paths.notification_outbox), outbox)

    return {
        "remediation_id": remediation_id,
        "due_date": due_date,
        "gate_status": gate_artifact.gate_status,
    }


def transition_status_api(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    remediation_id: str,
    to_status: str,
    note: str,
    operator_paths: RemediationOperatorPaths,
    evidence_files: Optional[List[Dict[str, object]]] = None,
    now: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, object]:
    actor = require_actor(actor_directory, actor_user_id)
    _require_role(actor, MUTATION_ROLES)

    items = load_lifecycle_items(Path(operator_paths.items))
    remediation = _find_remediation(items, remediation_id)
    _require_same_tenant(actor, remediation)
    _require_owner_or_privileged(actor, remediation)

    timeline = load_timeline(Path(operator_paths.timeline))
    audit_log = load_operator_audit_log(Path(operator_paths.operator_audit_log))
    outbox = load_notification_outbox(Path(operator_paths.notification_outbox))
    evidence_metadata_rows = load_evidence_metadata(Path(operator_paths.evidence_metadata))

    now_value = now or _utc_now_iso()
    evidence_files = evidence_files or []

    if to_status == "EVIDENCE_SUBMITTED":
        evidence_ids = [str(file["file_id"]) for file in evidence_files]
        updated_items, updated_timeline = submit_for_verification(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=remediation_id,
            actor_user_id=actor.user_id,
            note=note,
            evidence_file_ids=evidence_ids,
            now=now_value,
        )
        for file in evidence_files:
            evidence_metadata_rows = _append_evidence_metadata(
                evidence_metadata_rows,
                remediation_id=remediation_id,
                tenant_id=actor.tenant_id,
                audit_id=str(remediation["audit_id"]),
                uploaded_by_user_id=actor.user_id,
                file_id=str(file["file_id"]),
                filename=str(file["filename"]),
                content_type=str(file["content_type"]),
                sha256=str(file["sha256"]),
                byte_size=int(file["byte_size"]),
                now=now_value,
            )
        outbox = _append_notification(
            outbox,
            tenant_id=actor.tenant_id,
            remediation_id=remediation_id,
            event_type="REMEDIATION_EVIDENCE_SUBMITTED",
            recipient_user_ids=[str(remediation["owner_user_id"])] if remediation.get("owner_user_id") else [actor.user_id],
            payload={"remediation_id": remediation_id, "evidence_file_ids": evidence_ids},
            now=now_value,
        )
    else:
        updated_items, updated_timeline = transition_status(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=remediation_id,
            to_status=to_status,
            actor_user_id=actor.user_id,
            note=note,
            evidence_file_ids=None,
            now=now_value,
        )

    audit_log = _append_operator_audit_log(
        audit_log,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        action=f"STATUS_{to_status}",
        note=note,
        now=now_value,
    )

    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items, today=today)

    write_lifecycle_items(Path(operator_paths.items), updated_items)
    write_timeline(Path(operator_paths.timeline), updated_timeline)
    write_lifecycle_index(Path(operator_paths.lifecycle_index), index_artifact)
    write_lifecycle_gate(Path(operator_paths.gate), gate_artifact)
    write_evidence_metadata(Path(operator_paths.evidence_metadata), evidence_metadata_rows)
    write_operator_audit_log(Path(operator_paths.operator_audit_log), audit_log)
    write_notification_outbox(Path(operator_paths.notification_outbox), outbox)

    return {
        "remediation_id": remediation_id,
        "to_status": to_status,
        "gate_status": gate_artifact.gate_status,
    }


def apply_verification_result_api(
    *,
    actor_directory: Dict[str, Dict[str, object]],
    actor_user_id: str,
    remediation_id: str,
    verification_passed: bool,
    updated_gap_note: Optional[str],
    operator_paths: RemediationOperatorPaths,
    now: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, object]:
    actor = require_actor(actor_directory, actor_user_id)
    _require_role(actor, VERIFICATION_ROLES)

    items = load_lifecycle_items(Path(operator_paths.items))
    remediation = _find_remediation(items, remediation_id)
    _require_same_tenant(actor, remediation)

    timeline = load_timeline(Path(operator_paths.timeline))
    audit_log = load_operator_audit_log(Path(operator_paths.operator_audit_log))
    outbox = load_notification_outbox(Path(operator_paths.notification_outbox))

    now_value = now or _utc_now_iso()

    updated_items, updated_timeline = apply_verification_result(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=remediation_id,
        verification_passed=verification_passed,
        updated_gap_note=updated_gap_note,
        now=now_value,
    )

    audit_log = _append_operator_audit_log(
        audit_log,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        action="VERIFICATION_RESULT_APPLIED",
        note=(
            "Verification passed and remediation closed."
            if verification_passed
            else (updated_gap_note or "Verification failed and remediation reopened.")
        ),
        now=now_value,
    )
    outbox = _append_notification(
        outbox,
        tenant_id=actor.tenant_id,
        remediation_id=remediation_id,
        event_type="REMEDIATION_VERIFICATION_RESULT",
        recipient_user_ids=[str(remediation["owner_user_id"])] if remediation.get("owner_user_id") else [actor.user_id],
        payload={"remediation_id": remediation_id, "verification_passed": verification_passed},
        now=now_value,
    )

    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items, today=today)

    write_lifecycle_items(Path(operator_paths.items), updated_items)
    write_timeline(Path(operator_paths.timeline), updated_timeline)
    write_lifecycle_index(Path(operator_paths.lifecycle_index), index_artifact)
    write_lifecycle_gate(Path(operator_paths.gate), gate_artifact)
    write_operator_audit_log(Path(operator_paths.operator_audit_log), audit_log)
    write_notification_outbox(Path(operator_paths.notification_outbox), outbox)

    return {
        "remediation_id": remediation_id,
        "verification_passed": verification_passed,
        "gate_status": gate_artifact.gate_status,
    }
