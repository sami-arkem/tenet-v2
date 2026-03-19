from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REASON_RESULT_OUTCOME_SCHEMA_VERSION = "1.0"


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


@dataclass(frozen=True)
class ExecutionOutcome:
    job_id: str
    run_status: str
    execution_status: str
    verdict_status: str
    report_ready: bool
    export_ready: bool
    release_ready: bool
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionOutcomeArtifact:
    schema_version: str
    job_outcomes: Dict[str, Dict[str, object]]
    total_jobs_seen: int
    total_completed: int
    total_blocked: int
    total_failed: int
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "job_outcomes": self.job_outcomes,
            "total_jobs_seen": self.total_jobs_seen,
            "total_completed": self.total_completed,
            "total_blocked": self.total_blocked,
            "total_failed": self.total_failed,
            "payload_hash": self.payload_hash,
        }


def load_reason_results(path: Path) -> List[Dict[str, object]]:
    if path.suffix == ".jsonl":
        rows = _read_jsonl(path)
    else:
        payload = _read_json(path)
        raw = payload.get("results", payload)
        if isinstance(raw, list):
            rows = [row for row in raw if isinstance(row, dict)]
        else:
            rows = []
    rows.sort(key=lambda row: str(row.get("job_id") or row.get("audit_id") or ""))
    return rows


def _normalize_run_status(value: object) -> str:
    normalized = str(value or "FAILED").upper()
    allowed = {"COMPLETED", "FAILED", "RUNNING", "QUEUED"}
    return normalized if normalized in allowed else "FAILED"


def _normalize_execution_status(value: object) -> str:
    normalized = str(value or "BLOCKED").upper()
    allowed = {"COMPLETED", "BLOCKED", "FAILED", "RUNNING", "PENDING_EXECUTION", "NOT_STARTED"}
    return normalized if normalized in allowed else "FAILED"


def _normalize_verdict_status(value: object) -> str:
    normalized = str(value or "BLOCKED").upper()
    allowed = {
        "APPROVED",
        "CONDITIONALLY_APPROVED",
        "BLOCKED",
        "FAILED",
        "NOT_RUN",
    }
    return normalized if normalized in allowed else "FAILED"


def _derive_outcome_from_reason_result(result: Dict[str, object]) -> ExecutionOutcome:
    job_id = str(result.get("job_id") or result.get("audit_id") or "")
    if not job_id:
        raise ValueError("reason result missing job_id/audit_id")

    blocking_reasons = [str(x) for x in result.get("blocking_reasons", [])]

    raw_run_status = result.get("run_status")
    raw_execution_status = result.get("execution_status")
    raw_verdict_status = result.get("verdict_status") or result.get("deployment_decision")

    report_ready = bool(result.get("report_ready", False))
    export_ready = bool(result.get("export_ready", False))

    if raw_run_status is None:
        raw_run_status = "COMPLETED" if not blocking_reasons else "FAILED"

    if raw_execution_status is None:
        raw_execution_status = "COMPLETED" if not blocking_reasons else "BLOCKED"

    if raw_verdict_status is None:
        raw_verdict_status = "BLOCKED" if blocking_reasons else "CONDITIONALLY_APPROVED"

    run_status = _normalize_run_status(raw_run_status)
    execution_status = _normalize_execution_status(raw_execution_status)
    verdict_status = _normalize_verdict_status(raw_verdict_status)

    if run_status != "COMPLETED" and "deterministic_execution:not_completed" not in blocking_reasons:
        blocking_reasons.append("deterministic_execution:not_completed")

    if execution_status != "COMPLETED" and "deterministic_execution:execution_not_completed" not in blocking_reasons:
        blocking_reasons.append("deterministic_execution:execution_not_completed")

    if not report_ready and "report_surface:report_not_ready" not in blocking_reasons:
        blocking_reasons.append("report_surface:report_not_ready")

    if not export_ready and "export_surface:export_not_ready" not in blocking_reasons:
        blocking_reasons.append("export_surface:export_not_ready")

    release_ready = (
        run_status == "COMPLETED"
        and execution_status == "COMPLETED"
        and report_ready
        and export_ready
        and not blocking_reasons
    )

    return ExecutionOutcome(
        job_id=job_id,
        run_status=run_status,
        execution_status=execution_status,
        verdict_status=verdict_status,
        report_ready=report_ready,
        export_ready=export_ready,
        release_ready=release_ready,
        blocking_reasons=sorted(dict.fromkeys(blocking_reasons)),
    )


def build_execution_outcomes(results: Iterable[Dict[str, object]]) -> ExecutionOutcomeArtifact:
    job_outcomes: Dict[str, Dict[str, object]] = {}
    total_completed = 0
    total_blocked = 0
    total_failed = 0
    total_jobs_seen = 0

    for result in results:
        outcome = _derive_outcome_from_reason_result(result)
        job_outcomes[outcome.job_id] = outcome.to_dict()
        total_jobs_seen += 1

        if outcome.run_status == "FAILED" or outcome.execution_status == "FAILED":
            total_failed += 1
        elif outcome.execution_status == "COMPLETED":
            total_completed += 1
        else:
            total_blocked += 1

    payload = {
        "schema_version": REASON_RESULT_OUTCOME_SCHEMA_VERSION,
        "job_outcomes": job_outcomes,
        "total_jobs_seen": total_jobs_seen,
        "total_completed": total_completed,
        "total_blocked": total_blocked,
        "total_failed": total_failed,
    }

    return ExecutionOutcomeArtifact(
        schema_version=payload["schema_version"],
        job_outcomes=payload["job_outcomes"],
        total_jobs_seen=payload["total_jobs_seen"],
        total_completed=payload["total_completed"],
        total_blocked=payload["total_blocked"],
        total_failed=payload["total_failed"],
        payload_hash=_stable_json_hash(payload),
    )


def write_execution_outcomes(path: Path, artifact: ExecutionOutcomeArtifact) -> None:
    _write_json(path, artifact.to_dict())
