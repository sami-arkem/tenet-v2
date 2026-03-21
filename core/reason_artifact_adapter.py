from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REASON_ARTIFACT_ADAPTER_SCHEMA_VERSION = "1.0"


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
class CanonicalReasonArtifact:
    job_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: Optional[str]
    deterministic_decision: str
    report_ready: bool
    export_ready: bool
    findings_count: int
    missing_controls_count: int
    missing_evidence_count: int
    review_complete: bool
    export_verified: bool
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


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
class CanonicalExecutionOutcomeArtifact:
    schema_version: str
    source_contract: str
    canonical_reason_artifacts: List[CanonicalReasonArtifact]
    job_outcomes: Dict[str, Dict[str, object]]
    total_jobs_seen: int
    total_completed: int
    total_blocked: int
    total_failed: int
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_contract": self.source_contract,
            "canonical_reason_artifacts": [item.to_dict() for item in self.canonical_reason_artifacts],
            "job_outcomes": self.job_outcomes,
            "total_jobs_seen": self.total_jobs_seen,
            "total_completed": self.total_completed,
            "total_blocked": self.total_blocked,
            "total_failed": self.total_failed,
            "payload_hash": self.payload_hash,
        }


def load_reason_artifacts(path: Path) -> List[Dict[str, object]]:
    if path.suffix == ".jsonl":
        rows = _read_jsonl(path)
    else:
        payload = _read_json(path)
        raw = payload.get("artifacts", payload.get("results", payload))
        if isinstance(raw, list):
            rows = [row for row in raw if isinstance(row, dict)]
        else:
            rows = []
    rows.sort(key=lambda row: str(row.get("job_id") or row.get("audit_id") or ""))
    return rows


def _normalize_decision(value: object) -> str:
    normalized = str(value or "BLOCKED").upper()
    allowed = {"APPROVED", "CONDITIONALLY_APPROVED", "BLOCKED"}
    return normalized if normalized in allowed else "BLOCKED"


def _derive_blocking_reasons(artifact: Dict[str, object]) -> List[str]:
    blocking_reasons = [str(x) for x in artifact.get("blocking_reasons", [])]

    missing_controls = int(artifact.get("missing_controls_count", len(artifact.get("missing_controls", [])) if isinstance(artifact.get("missing_controls"), list) else 0))
    missing_evidence = int(artifact.get("missing_evidence_count", len(artifact.get("missing_evidence", [])) if isinstance(artifact.get("missing_evidence"), list) else 0))
    review_complete = bool(artifact.get("review_complete", False))
    export_verified = bool(artifact.get("export_verified", False))
    report_ready = bool(artifact.get("report_ready", False))
    export_ready = bool(artifact.get("export_ready", False))
    deterministic_decision = _normalize_decision(artifact.get("deployment_decision") or artifact.get("deterministic_decision"))

    if missing_controls > 0:
        blocking_reasons.append(f"controls:missing:{missing_controls}")
    if missing_evidence > 0:
        blocking_reasons.append(f"evidence:missing:{missing_evidence}")
    if not review_complete:
        blocking_reasons.append("review:incomplete")
    if not report_ready:
        blocking_reasons.append("report_surface:report_not_ready")
    if not export_ready:
        blocking_reasons.append("export_surface:export_not_ready")
    if not export_verified:
        blocking_reasons.append("export_surface:export_not_verified")
    if deterministic_decision == "BLOCKED":
        blocking_reasons.append("deterministic_decision:blocked")

    return sorted(dict.fromkeys(blocking_reasons))


def _canonicalize_reason_artifact(raw: Dict[str, object]) -> CanonicalReasonArtifact:
    job_id = str(raw.get("job_id") or raw.get("audit_id") or "")
    audit_id = str(raw.get("audit_id") or job_id)
    tenant_id = str(raw.get("tenant_id") or "")
    audit_kind = str(raw.get("audit_kind") or "")
    schedule_id = str(raw.get("schedule_id")) if raw.get("schedule_id") is not None else None

    if not job_id:
        raise ValueError("reason artifact missing job_id/audit_id")
    if not tenant_id:
        raise ValueError(f"reason artifact missing tenant_id for {job_id}")
    if not audit_kind:
        raise ValueError(f"reason artifact missing audit_kind for {job_id}")

    deterministic_decision = _normalize_decision(
        raw.get("deployment_decision") or raw.get("deterministic_decision")
    )
    report_ready = bool(raw.get("report_ready", False))
    export_ready = bool(raw.get("export_ready", False))
    findings_count = int(raw.get("findings_count", len(raw.get("findings", [])) if isinstance(raw.get("findings"), list) else 0))
    missing_controls_count = int(raw.get("missing_controls_count", len(raw.get("missing_controls", [])) if isinstance(raw.get("missing_controls"), list) else 0))
    missing_evidence_count = int(raw.get("missing_evidence_count", len(raw.get("missing_evidence", [])) if isinstance(raw.get("missing_evidence"), list) else 0))
    review_complete = bool(raw.get("review_complete", False))
    export_verified = bool(raw.get("export_verified", False))
    blocking_reasons = _derive_blocking_reasons(raw)

    payload = {
        "job_id": job_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": audit_kind,
        "schedule_id": schedule_id,
        "deterministic_decision": deterministic_decision,
        "report_ready": report_ready,
        "export_ready": export_ready,
        "findings_count": findings_count,
        "missing_controls_count": missing_controls_count,
        "missing_evidence_count": missing_evidence_count,
        "review_complete": review_complete,
        "export_verified": export_verified,
        "blocking_reasons": blocking_reasons,
    }

    return CanonicalReasonArtifact(
        job_id=payload["job_id"],
        audit_id=payload["audit_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        deterministic_decision=payload["deterministic_decision"],
        report_ready=payload["report_ready"],
        export_ready=payload["export_ready"],
        findings_count=payload["findings_count"],
        missing_controls_count=payload["missing_controls_count"],
        missing_evidence_count=payload["missing_evidence_count"],
        review_complete=payload["review_complete"],
        export_verified=payload["export_verified"],
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def _to_execution_outcome(artifact: CanonicalReasonArtifact) -> ExecutionOutcome:
    if artifact.blocking_reasons:
        run_status = "FAILED"
        execution_status = "BLOCKED"
    else:
        run_status = "COMPLETED"
        execution_status = "COMPLETED"

    verdict_status = artifact.deterministic_decision
    release_ready = (
        run_status == "COMPLETED"
        and execution_status == "COMPLETED"
        and artifact.report_ready
        and artifact.export_ready
        and not artifact.blocking_reasons
    )

    return ExecutionOutcome(
        job_id=artifact.job_id,
        run_status=run_status,
        execution_status=execution_status,
        verdict_status=verdict_status,
        report_ready=artifact.report_ready,
        export_ready=artifact.export_ready,
        release_ready=release_ready,
        blocking_reasons=artifact.blocking_reasons,
    )


def build_canonical_execution_outcomes(raw_artifacts: Iterable[Dict[str, object]]) -> CanonicalExecutionOutcomeArtifact:
    canonical_reason_artifacts: List[CanonicalReasonArtifact] = []
    job_outcomes: Dict[str, Dict[str, object]] = {}
    total_jobs_seen = 0
    total_completed = 0
    total_blocked = 0
    total_failed = 0

    for raw in raw_artifacts:
        canonical = _canonicalize_reason_artifact(raw)
        outcome = _to_execution_outcome(canonical)

        canonical_reason_artifacts.append(canonical)
        job_outcomes[canonical.job_id] = outcome.to_dict()
        total_jobs_seen += 1

        if outcome.run_status == "COMPLETED" and outcome.execution_status == "COMPLETED":
            total_completed += 1
        elif outcome.run_status == "FAILED":
            total_failed += 1
        else:
            total_blocked += 1

    canonical_reason_artifacts.sort(key=lambda item: item.job_id)

    payload = {
        "schema_version": REASON_ARTIFACT_ADAPTER_SCHEMA_VERSION,
        "source_contract": "canonical_reason_artifact_v1",
        "canonical_reason_artifacts": [item.to_dict() for item in canonical_reason_artifacts],
        "job_outcomes": job_outcomes,
        "total_jobs_seen": total_jobs_seen,
        "total_completed": total_completed,
        "total_blocked": total_blocked,
        "total_failed": total_failed,
    }

    return CanonicalExecutionOutcomeArtifact(
        schema_version=payload["schema_version"],
        source_contract=payload["source_contract"],
        canonical_reason_artifacts=canonical_reason_artifacts,
        job_outcomes=payload["job_outcomes"],
        total_jobs_seen=payload["total_jobs_seen"],
        total_completed=payload["total_completed"],
        total_blocked=payload["total_blocked"],
        total_failed=payload["total_failed"],
        payload_hash=_stable_json_hash(payload),
    )


def write_canonical_execution_outcomes(path: Path, artifact: CanonicalExecutionOutcomeArtifact) -> None:
    _write_json(path, artifact.to_dict())
