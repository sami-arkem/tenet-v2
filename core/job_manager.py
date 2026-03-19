from __future__ import annotations

import json
import os
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Any, Callable

from core import evidence_processing_service, workflow_service


DEFAULT_JOB_ROOT = Path("artifacts") / "jobs"

QUEUE_EVIDENCE_PROCESSING = "evidence_processing"
QUEUE_AI_TASKS = "ai_tasks"
QUEUE_AUDIT_RUNS = "audit_runs"
QUEUE_REPORTS = "reports"
QUEUE_SCHEDULED = "scheduled"

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_SUCCEEDED = "SUCCEEDED"
STATUS_FAILED = "FAILED"

VALID_QUEUES = {
    QUEUE_EVIDENCE_PROCESSING,
    QUEUE_AI_TASKS,
    QUEUE_AUDIT_RUNS,
    QUEUE_REPORTS,
    QUEUE_SCHEDULED,
}

VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    STATUS_FAILED,
}


_LOCAL_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tenet_jobs")
_WRITE_LOCK = Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:16]}"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    with _WRITE_LOCK:
        _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _job_path(job_id: str, job_root: Path = DEFAULT_JOB_ROOT) -> Path:
    job_id = _require_non_empty_str(job_id, "job_id")
    return job_root / f"{job_id}.json"


def _validate_queue(queue_name: str) -> str:
    queue_name = _require_non_empty_str(queue_name, "queue_name")
    if queue_name not in VALID_QUEUES:
        raise ValueError(f"queue_name must be one of {sorted(VALID_QUEUES)}")
    return queue_name


def _validate_status(status: str) -> str:
    status = _require_non_empty_str(status, "status")
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
    return status


def create_job_record(
    *,
    job_type: str,
    queue_name: str,
    payload: dict[str, Any],
    max_retries: int,
    time_limit_seconds: int,
    job_root: Path = DEFAULT_JOB_ROOT,
) -> dict[str, Any]:
    job_type = _require_non_empty_str(job_type, "job_type")
    queue_name = _validate_queue(queue_name)
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("max_retries must be non-negative int")
    if not isinstance(time_limit_seconds, int) or time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive int")

    job_id = new_job_id()
    now = utc_now_iso()
    record = {
        "job_id": job_id,
        "job_type": job_type,
        "queue_name": queue_name,
        "status": STATUS_PENDING,
        "payload": payload,
        "result": None,
        "error": None,
        "retry_count": 0,
        "max_retries": max_retries,
        "time_limit_seconds": time_limit_seconds,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "timeline": [
            {
                "created_at": now,
                "event_type": "job_created",
                "payload": {
                    "job_type": job_type,
                    "queue_name": queue_name,
                },
            }
        ],
    }
    _atomic_write_json(_job_path(job_id, job_root), record)
    return record


def get_job(job_id: str, job_root: Path = DEFAULT_JOB_ROOT) -> dict[str, Any]:
    path = _job_path(job_id, job_root)
    if not path.exists():
        raise FileNotFoundError(f"job not found: {job_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("job record must be object")
    return payload


def _append_event(record: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
    record.setdefault("timeline", [])
    record["timeline"].append(
        {
            "created_at": utc_now_iso(),
            "event_type": event_type,
            "payload": payload,
        }
    )
    record["updated_at"] = utc_now_iso()


def _save_job(record: dict[str, Any], job_root: Path = DEFAULT_JOB_ROOT) -> None:
    _validate_status(record["status"])
    _atomic_write_json(_job_path(record["job_id"], job_root), record)


def _run_job_callable(
    *,
    job_id: str,
    fn: Callable[[dict[str, Any]], dict[str, Any]],
    job_root: Path,
) -> None:
    record = get_job(job_id, job_root)
    record["status"] = STATUS_RUNNING
    record["started_at"] = utc_now_iso()
    record["updated_at"] = utc_now_iso()
    _append_event(record, "job_started", {"job_type": record["job_type"]})
    _save_job(record, job_root)

    try:
        result = fn(record["payload"])
        if not isinstance(result, dict):
            raise ValueError("job function must return an object")
        record["status"] = STATUS_SUCCEEDED
        record["result"] = result
        record["finished_at"] = utc_now_iso()
        record["updated_at"] = utc_now_iso()
        _append_event(record, "job_succeeded", {"result_keys": sorted(result.keys())})
        _save_job(record, job_root)
    except Exception as exc:
        record["status"] = STATUS_FAILED
        record["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(limit=20),
        }
        record["finished_at"] = utc_now_iso()
        record["updated_at"] = utc_now_iso()
        _append_event(record, "job_failed", {"message": str(exc)})
        _save_job(record, job_root)


def _evidence_processing_job(payload: dict[str, Any]) -> dict[str, Any]:
    pack_id = _require_non_empty_str(payload.get("pack_id"), "payload.pack_id")
    out = evidence_processing_service.process_all_evidence_for_pack(
        pack_id=pack_id,
        pack_root=evidence_processing_service.DEFAULT_PACK_ROOT,
    )
    return {
        "pack_id": out["pack_id"],
        "processed_count": out["processed_count"],
        "failure_count": out["failure_count"],
        "readiness": out["readiness"],
    }


def _audit_execution_job(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_id = _require_non_empty_str(payload.get("workflow_id"), "payload.workflow_id")
    run_id = _require_non_empty_str(payload.get("run_id"), "payload.run_id")
    default_remediation_owner = _require_non_empty_str(
        payload.get("default_remediation_owner"),
        "payload.default_remediation_owner",
    )
    export = payload.get("export")
    metadata = payload.get("metadata")

    workflow_service.refresh_workflow_readiness(
        workflow_id,
        workflow_root=workflow_service.DEFAULT_WORKFLOW_ROOT,
        pack_root=workflow_service.DEFAULT_PACK_ROOT,
    )
    out = workflow_service.execute_workflow_audit(
        workflow_id=workflow_id,
        run_id=run_id,
        default_remediation_owner=default_remediation_owner,
        export=export if isinstance(export, dict) else None,
        metadata=metadata if isinstance(metadata, dict) else None,
        workflow_root=workflow_service.DEFAULT_WORKFLOW_ROOT,
        pack_root=workflow_service.DEFAULT_PACK_ROOT,
    )
    latest_execution = out.get("latest_execution")
    return {
        "workflow_id": workflow_id,
        "status": out["status"],
        "latest_execution": latest_execution,
    }


JOB_REGISTRY: dict[str, dict[str, Any]] = {
    "process_evidence_pack": {
        "queue_name": QUEUE_EVIDENCE_PROCESSING,
        "max_retries": 3,
        "time_limit_seconds": 300,
        "fn": _evidence_processing_job,
    },
    "run_workflow_audit": {
        "queue_name": QUEUE_AUDIT_RUNS,
        "max_retries": 1,
        "time_limit_seconds": 1800,
        "fn": _audit_execution_job,
    },
}


def submit_job(
    *,
    job_type: str,
    payload: dict[str, Any],
    job_root: Path = DEFAULT_JOB_ROOT,
) -> dict[str, Any]:
    job_type = _require_non_empty_str(job_type, "job_type")
    if job_type not in JOB_REGISTRY:
        raise ValueError(f"unsupported job_type: {job_type}")

    spec = JOB_REGISTRY[job_type]
    record = create_job_record(
        job_type=job_type,
        queue_name=spec["queue_name"],
        payload=payload,
        max_retries=spec["max_retries"],
        time_limit_seconds=spec["time_limit_seconds"],
        job_root=job_root,
    )

    _LOCAL_EXECUTOR.submit(
        _run_job_callable,
        job_id=record["job_id"],
        fn=spec["fn"],
        job_root=job_root,
    )
    return record


def list_jobs(job_root: Path = DEFAULT_JOB_ROOT) -> list[dict[str, Any]]:
    if not job_root.exists():
        return []

    rows: list[dict[str, Any]] = []
    for path in sorted(job_root.glob("job_*.json")):
        try:
            row = _load_json(path)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)

    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows
