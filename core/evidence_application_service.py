from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from apps.api.schemas.evidence import (
    AuditEvidenceGateResponse,
    EvidenceDetail,
    EvidenceListResponse,
    EvidenceSummary,
)


def _now_iso() -> str:
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


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class EvidenceApplicationPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.evidence_items = f"{base}/evidence/evidence_items.jsonl"
        self.audit_gates_dir = f"{base}/evidence"


def _load_items(paths: EvidenceApplicationPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.evidence_items))
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["created_at"], row["evidence_id"]))
    return rows


def _write_items(paths: EvidenceApplicationPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_id"], row["created_at"], row["evidence_id"]))
    _write_jsonl(Path(paths.evidence_items), rows)


def _audit_gate_path(paths: EvidenceApplicationPaths, audit_id: str) -> Path:
    return Path(paths.audit_gates_dir) / audit_id / "audit_evidence_gate.json"


def _audit_requirements_path(paths: EvidenceApplicationPaths, audit_id: str) -> Path:
    return Path(paths.audit_gates_dir) / audit_id / "audit_evidence_requirements.json"


def _find_item(rows: List[Dict[str, object]], evidence_id: str) -> Dict[str, object]:
    for row in rows:
        if str(row["evidence_id"]) == evidence_id:
            return row
    raise ValueError(f"Evidence not found: {evidence_id}")


def _require_same_tenant(tenant_id: str, row: Dict[str, object]) -> None:
    if str(row["tenant_id"]) != tenant_id:
        raise PermissionError("Forbidden")


def _assert_mutable(row: Dict[str, object]) -> None:
    if str(row.get("status")) == "READY":
        raise ValueError("EVIDENCE_IMMUTABLE: Ready evidence cannot be modified")


def _version_number(rows: List[Dict[str, object]], audit_id: str, sha256: str) -> int:
    same_family = [
        row for row in rows
        if str(row["audit_id"]) == audit_id and str(row["sha256"]) == sha256
    ]
    return len(same_family) + 1


def _to_summary(row: Dict[str, object]) -> EvidenceSummary:
    return EvidenceSummary(
        evidence_id=row["evidence_id"],
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        sha256=row["sha256"],
        byte_size=int(row["byte_size"]),
        evidence_category=row["evidence_category"],
        status=row["status"],
        supersedes_id=row.get("supersedes_id"),
        version_number=int(row["version_number"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _to_detail(row: Dict[str, object]) -> EvidenceDetail:
    return EvidenceDetail(
        evidence_id=row["evidence_id"],
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        sha256=row["sha256"],
        byte_size=int(row["byte_size"]),
        evidence_category=row["evidence_category"],
        status=row["status"],
        supersedes_id=row.get("supersedes_id"),
        version_number=int(row["version_number"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        storage_path=row.get("storage_path"),
        processing_error=row.get("processing_error"),
        extracted_text_ready=bool(row.get("extracted_text_ready", False)),
        inventory_ready=bool(row.get("inventory_ready", False)),
        immutable_after_ready=bool(row.get("immutable_after_ready", False)),
        note=row.get("note"),
    )


def register_upload(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    actor_user_id: str,
    payload: Dict[str, object],
) -> EvidenceSummary:
    rows = _load_items(paths)
    audit_id = str(payload["audit_id"])
    sha256 = str(payload["sha256"])

    for row in rows:
        if (
            str(row["tenant_id"]) == tenant_id
            and str(row["audit_id"]) == audit_id
            and str(row["sha256"]) == sha256
            and str(row["status"]) != "CANCELLED"
        ):
            raise ValueError("EVIDENCE_DUPLICATE: This file has already been uploaded")

    now = _now_iso()
    import uuid
    evidence_id = f"{tenant_id}:{audit_id}:evidence:{now}:{uuid.uuid4().hex[:8]}"
    row = {
        "evidence_id": evidence_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "uploaded_by_user_id": actor_user_id,
        "filename": str(payload["filename"]),
        "content_type": str(payload["content_type"]),
        "sha256": sha256,
        "byte_size": int(payload["byte_size"]),
        "evidence_category": str(payload["evidence_category"]),
        "status": "UPLOADING",
        "supersedes_id": payload.get("supersedes_id"),
        "version_number": _version_number(rows, audit_id, sha256),
        "storage_path": None,
        "processing_error": None,
        "extracted_text_ready": False,
        "inventory_ready": False,
        "immutable_after_ready": False,
        "note": payload.get("note"),
        "created_at": now,
        "updated_at": now,
    }
    row["payload_hash"] = _stable_json_hash(row)
    rows.append(row)
    _write_items(paths, rows)
    return _to_summary(row)


def complete_upload(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
    storage_path: str,
    processing_started: bool,
) -> EvidenceDetail:
    rows = _load_items(paths)
    updated: List[Dict[str, object]] = []

    for row in rows:
        row = dict(row)
        if str(row["evidence_id"]) == evidence_id:
            _require_same_tenant(tenant_id, row)
            _assert_mutable(row)
            if str(row["status"]) != "UPLOADING":
                raise ValueError("Invalid evidence status transition")
            row["storage_path"] = storage_path
            row["status"] = "PROCESSING" if processing_started else "UPLOADING"
            row["updated_at"] = _now_iso()
            row["payload_hash"] = _stable_json_hash(row)
        updated.append(row)

    _write_items(paths, updated)
    return _to_detail(_find_item(updated, evidence_id))


def fail_upload(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
    error_message: str,
) -> EvidenceDetail:
    rows = _load_items(paths)
    updated: List[Dict[str, object]] = []

    for row in rows:
        row = dict(row)
        if str(row["evidence_id"]) == evidence_id:
            _require_same_tenant(tenant_id, row)
            _assert_mutable(row)
            row["status"] = "FAILED"
            row["processing_error"] = error_message
            row["updated_at"] = _now_iso()
            row["payload_hash"] = _stable_json_hash(row)
        updated.append(row)

    _write_items(paths, updated)
    return _to_detail(_find_item(updated, evidence_id))


def cancel_upload(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
) -> EvidenceDetail:
    rows = _load_items(paths)
    updated: List[Dict[str, object]] = []

    for row in rows:
        row = dict(row)
        if str(row["evidence_id"]) == evidence_id:
            _require_same_tenant(tenant_id, row)
            _assert_mutable(row)
            row["status"] = "CANCELLED"
            row["storage_path"] = None
            row["updated_at"] = _now_iso()
            row["payload_hash"] = _stable_json_hash(row)
        updated.append(row)

    _write_items(paths, updated)
    return _to_detail(_find_item(updated, evidence_id))


def mark_ready(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
    extracted_text_ready: bool,
    inventory_ready: bool,
) -> EvidenceDetail:
    rows = _load_items(paths)
    updated: List[Dict[str, object]] = []

    for row in rows:
        row = dict(row)
        if str(row["evidence_id"]) == evidence_id:
            _require_same_tenant(tenant_id, row)
            _assert_mutable(row)
            if str(row["status"]) not in {"PROCESSING", "UPLOADING"}:
                raise ValueError("Invalid evidence status transition")
            row["status"] = "READY"
            row["extracted_text_ready"] = extracted_text_ready
            row["inventory_ready"] = inventory_ready
            row["immutable_after_ready"] = True
            row["updated_at"] = _now_iso()
            row["payload_hash"] = _stable_json_hash(row)
        updated.append(row)

    _write_items(paths, updated)
    return _to_detail(_find_item(updated, evidence_id))


def list_evidence(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    audit_id: Optional[str] = None,
) -> EvidenceListResponse:
    rows = _load_items(paths)
    scoped = [row for row in rows if str(row["tenant_id"]) == tenant_id]
    if audit_id:
        scoped = [row for row in scoped if str(row["audit_id"]) == audit_id]

    return EvidenceListResponse(
        audit_id=audit_id,
        total_items=len(scoped),
        total_ready=sum(1 for row in scoped if str(row["status"]) == "READY"),
        total_processing=sum(1 for row in scoped if str(row["status"]) in {"UPLOADING", "PROCESSING"}),
        total_failed=sum(1 for row in scoped if str(row["status"]) == "FAILED"),
        total_cancelled=sum(1 for row in scoped if str(row["status"]) == "CANCELLED"),
        rows=[_to_summary(row) for row in scoped],
    )


def get_evidence_detail(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
) -> EvidenceDetail:
    row = _find_item(_load_items(paths), evidence_id)
    _require_same_tenant(tenant_id, row)
    return _to_detail(row)


def recompute_audit_evidence_gate(
    *,
    paths: EvidenceApplicationPaths,
    tenant_id: str,
    audit_id: str,
) -> AuditEvidenceGateResponse:
    requirements_payload = _read_json(_audit_requirements_path(paths, audit_id))
    required_categories = list(requirements_payload.get("required_categories", []))
    rows = [row for row in _load_items(paths) if str(row["tenant_id"]) == tenant_id and str(row["audit_id"]) == audit_id]

    ready_rows = [row for row in rows if str(row["status"]) == "READY"]
    waiting_rows = [row for row in rows if str(row["status"]) in {"UPLOADING", "PROCESSING"}]
    ready_categories = sorted({str(row["evidence_category"]) for row in ready_rows})

    missing_categories = [cat for cat in required_categories if cat not in ready_categories]
    blocking_reasons: List[str] = []

    if waiting_rows:
        blocking_reasons.append(f"Waiting for {len(waiting_rows)} files to finish processing")
    if missing_categories:
        blocking_reasons.append("Required evidence is missing")

    gate_status = "PASS" if not blocking_reasons else "BLOCKED"
    evidence_ready = gate_status == "PASS"

    payload = {
        "audit_id": audit_id,
        "gate_name": "audit_evidence_gate",
        "gate_status": gate_status,
        "evidence_ready": evidence_ready,
        "waiting_file_count": len(waiting_rows),
        "total_files": len(rows),
        "total_ready_files": len(ready_rows),
        "blocking_reasons": blocking_reasons,
        "required_categories": required_categories,
        "ready_categories": ready_categories,
    }
    _write_json(_audit_gate_path(paths, audit_id), payload)

    return AuditEvidenceGateResponse(
        audit_id=audit_id,
        gate_name=payload["gate_name"],
        gate_status=payload["gate_status"],
        evidence_ready=payload["evidence_ready"],
        waiting_file_count=payload["waiting_file_count"],
        total_files=payload["total_files"],
        total_ready_files=payload["total_ready_files"],
        blocking_reasons=payload["blocking_reasons"],
        required_categories=payload["required_categories"],
        ready_categories=payload["ready_categories"],
    )


def seed_audit_requirements(
    *,
    paths: EvidenceApplicationPaths,
    audit_id: str,
    required_categories: List[str],
) -> None:
    payload = {
        "audit_id": audit_id,
        "required_categories": sorted(dict.fromkeys(required_categories)),
    }
    _write_json(_audit_requirements_path(paths, audit_id), payload)
