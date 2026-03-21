from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from apps.api.schemas.evidence_jobs import EvidenceJobListResponse, EvidenceJobSummary
from core.evidence_application_service import EvidenceApplicationPaths, mark_ready


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


class EvidenceJobPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.jobs = f"{base}/evidence/evidence_jobs.jsonl"


def _load_jobs(paths: EvidenceJobPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.jobs))
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["job_id"]))
    return rows


def _write_jobs(paths: EvidenceJobPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["job_id"]))
    _write_jsonl(Path(paths.jobs), rows)


def _to_summary(row: Dict[str, object]) -> EvidenceJobSummary:
    return EvidenceJobSummary(
        job_id=row["job_id"],
        evidence_id=row["evidence_id"],
        audit_id=row["audit_id"],
        tenant_id=row["tenant_id"],
        status=row["status"],
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def enqueue_job(
    *,
    job_paths: EvidenceJobPaths,
    evidence_paths: EvidenceApplicationPaths,
    tenant_id: str,
    evidence_id: str,
) -> EvidenceJobSummary:
    rows = _load_jobs(job_paths)
    now = _now_iso()
    job_id = f"{tenant_id}:{evidence_id}:job:{now}"

    row = {
        "job_id": job_id,
        "evidence_id": evidence_id,
        "audit_id": None,
        "tenant_id": tenant_id,
        "status": "QUEUED",
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    rows.append(row)
    _write_jobs(job_paths, rows)
    return _to_summary(row)


def list_jobs(
    *,
    paths: EvidenceJobPaths,
    tenant_id: str,
    status: Optional[str] = None,
) -> EvidenceJobListResponse:
    rows = [row for row in _load_jobs(paths) if str(row["tenant_id"]) == tenant_id]
    if status:
        rows = [row for row in rows if str(row["status"]) == status]

    return EvidenceJobListResponse(
        total_items=len(rows),
        total_queued=sum(1 for row in rows if str(row["status"]) == "QUEUED"),
        total_processing=sum(1 for row in rows if str(row["status"]) == "PROCESSING"),
        total_completed=sum(1 for row in rows if str(row["status"]) == "COMPLETED"),
        total_failed=sum(1 for row in rows if str(row["status"]) == "FAILED"),
        rows=[_to_summary(row) for row in rows],
    )


def run_next_job(
    *,
    job_paths: EvidenceJobPaths,
    evidence_paths: EvidenceApplicationPaths,
    tenant_id: str,
    actor_user_id: str,
) -> Optional[EvidenceJobSummary]:
    rows = _load_jobs(job_paths)
    queued = [row for row in rows if str(row["tenant_id"]) == tenant_id and str(row["status"]) == "QUEUED"]

    if not queued:
        return None

    job = queued[0]
    job["status"] = "PROCESSING"
    job["updated_at"] = _now_iso()
    _write_jobs(job_paths, rows)

    try:
        mark_ready(
            paths=evidence_paths,
            tenant_id=tenant_id,
            evidence_id=job["evidence_id"],
            extracted_text_ready=True,
            inventory_ready=True,
        )
        job["status"] = "COMPLETED"
    except Exception as e:
        job["status"] = "FAILED"
        job["error_message"] = str(e)

    job["updated_at"] = _now_iso()
    _write_jobs(job_paths, rows)
    return _to_summary(job)
