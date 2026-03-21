from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from apps.api.schemas.upload_sessions import UploadSessionListResponse, UploadSessionSummary
from core.blob_store import BlobStorePaths, promote_to_blob_store
from core.evidence_application_service import (
    EvidenceApplicationPaths,
    register_upload,
    complete_upload,
)
from core.evidence_job_service import EvidenceJobPaths, enqueue_job


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


class UploadSessionPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.sessions = f"{base}/uploads/upload_sessions.jsonl"


def _load_sessions(paths: UploadSessionPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.sessions))
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["upload_session_id"]))
    return rows


def _write_sessions(paths: UploadSessionPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["upload_session_id"]))
    _write_jsonl(Path(paths.sessions), rows)


def _find_session(rows: List[Dict[str, object]], upload_session_id: str) -> Dict[str, object]:
    for row in rows:
        if str(row["upload_session_id"]) == upload_session_id:
            return row
    raise ValueError(f"Upload session not found: {upload_session_id}")


def _require_same_tenant(tenant_id: str, row: Dict[str, object]) -> None:
    if str(row["tenant_id"]) != tenant_id:
        raise PermissionError("Forbidden")


def _to_summary(row: Dict[str, object]) -> UploadSessionSummary:
    return UploadSessionSummary(
        upload_session_id=row["upload_session_id"],
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        sha256=row["sha256"],
        byte_size=int(row["byte_size"]),
        evidence_category=row["evidence_category"],
        status=row["status"],
        blob_id=row.get("blob_id"),
        storage_path=row.get("storage_path"),
        evidence_id=row.get("evidence_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_upload_session(
    *,
    paths: UploadSessionPaths,
    tenant_id: str,
    actor_user_id: str,
    payload: Dict[str, object],
) -> UploadSessionSummary:
    rows = _load_sessions(paths)
    now = _now_iso()
    upload_session_id = f"{tenant_id}:{payload['audit_id']}:upload:{now}:{len(rows)+1}"

    row = {
        "upload_session_id": upload_session_id,
        "audit_id": str(payload["audit_id"]),
        "tenant_id": tenant_id,
        "created_by_user_id": actor_user_id,
        "filename": str(payload["filename"]),
        "content_type": str(payload["content_type"]),
        "sha256": str(payload["sha256"]),
        "byte_size": int(payload["byte_size"]),
        "evidence_category": str(payload["evidence_category"]),
        "note": payload.get("note"),
        "supersedes_id": payload.get("supersedes_id"),
        "status": "CREATED",
        "blob_id": None,
        "storage_path": None,
        "evidence_id": None,
        "processing_error": None,
        "created_at": now,
        "updated_at": now,
    }
    rows.append(row)
    _write_sessions(paths, rows)
    return _to_summary(row)


def list_upload_sessions(
    *,
    paths: UploadSessionPaths,
    tenant_id: str,
    audit_id: Optional[str] = None,
) -> UploadSessionListResponse:
    rows = [row for row in _load_sessions(paths) if str(row["tenant_id"]) == tenant_id]
    if audit_id:
        rows = [row for row in rows if str(row["audit_id"]) == audit_id]

    return UploadSessionListResponse(
        total_items=len(rows),
        total_created=sum(1 for row in rows if str(row["status"]) == "CREATED"),
        total_uploading=sum(1 for row in rows if str(row["status"]) == "UPLOADING"),
        total_finalizing=sum(1 for row in rows if str(row["status"]) == "FINALIZING"),
        total_completed=sum(1 for row in rows if str(row["status"]) == "COMPLETED"),
        total_failed=sum(1 for row in rows if str(row["status"]) == "FAILED"),
        total_cancelled=sum(1 for row in rows if str(row["status"]) == "CANCELLED"),
        rows=[_to_summary(row) for row in rows],
    )


def finalize_upload_session(
    *,
    session_paths: UploadSessionPaths,
    blob_paths: BlobStorePaths,
    evidence_paths: EvidenceApplicationPaths,
    job_paths: EvidenceJobPaths,
    tenant_id: str,
    actor_user_id: str,
    upload_session_id: str,
    temp_file_path: str,
) -> UploadSessionSummary:
    rows = _load_sessions(session_paths)
    session = _find_session(rows, upload_session_id)
    _require_same_tenant(tenant_id, session)

    if str(session["status"]) in {"COMPLETED", "CANCELLED"}:
        raise ValueError("Invalid upload session status transition")

    session["status"] = "FINALIZING"
    session["updated_at"] = _now_iso()

    promoted = promote_to_blob_store(
        paths=blob_paths,
        tenant_id=tenant_id,
        audit_id=str(session["audit_id"]),
        upload_session_id=upload_session_id,
        filename=str(session["filename"]),
        content_type=str(session["content_type"]),
        sha256=str(session["sha256"]),
        byte_size=int(session["byte_size"]),
        temp_file_path=Path(temp_file_path),
    )

    evidence = register_upload(
        paths=evidence_paths,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        payload={
            "audit_id": session["audit_id"],
            "filename": session["filename"],
            "content_type": session["content_type"],
            "sha256": session["sha256"],
            "byte_size": session["byte_size"],
            "evidence_category": session["evidence_category"],
            "note": session.get("note"),
            "supersedes_id": session.get("supersedes_id"),
        },
    )
    complete_upload(
        paths=evidence_paths,
        tenant_id=tenant_id,
        evidence_id=evidence.evidence_id,
        storage_path=str(promoted["storage_path"]),
        processing_started=True,
    )
    enqueue_job(
        job_paths=job_paths,
        evidence_paths=evidence_paths,
        tenant_id=tenant_id,
        evidence_id=evidence.evidence_id,
    )

    for row in rows:
        if str(row["upload_session_id"]) == upload_session_id:
            row["status"] = "COMPLETED"
            row["blob_id"] = promoted["blob_id"]
            row["storage_path"] = promoted["storage_path"]
            row["evidence_id"] = evidence.evidence_id
            row["updated_at"] = _now_iso()

    _write_sessions(session_paths, rows)
    return _to_summary(_find_session(rows, upload_session_id))


def fail_upload_session(
    *,
    paths: UploadSessionPaths,
    tenant_id: str,
    upload_session_id: str,
    error_message: str,
) -> UploadSessionSummary:
    rows = _load_sessions(paths)
    for row in rows:
        if str(row["upload_session_id"]) == upload_session_id:
            _require_same_tenant(tenant_id, row)
            row["status"] = "FAILED"
            row["processing_error"] = error_message
            row["updated_at"] = _now_iso()
    _write_sessions(paths, rows)
    return _to_summary(_find_session(rows, upload_session_id))


def cancel_upload_session(
    *,
    paths: UploadSessionPaths,
    tenant_id: str,
    upload_session_id: str,
) -> UploadSessionSummary:
    rows = _load_sessions(paths)
    for row in rows:
        if str(row["upload_session_id"]) == upload_session_id:
            _require_same_tenant(tenant_id, row)
            if str(row["status"]) == "COMPLETED":
                raise ValueError("Invalid upload session status transition")
            row["status"] = "CANCELLED"
            row["updated_at"] = _now_iso()
    _write_sessions(paths, rows)
    return _to_summary(_find_session(rows, upload_session_id))
