from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REASON_OUTPUT_BRIDGE_SCHEMA_VERSION = "1.0"


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


def _count_list(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


@dataclass(frozen=True)
class CanonicalReasonArtifact:
    job_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    schedule_id: Optional[str]
    deployment_decision: str
    findings_count: int
    missing_controls_count: int
    missing_evidence_count: int
    review_complete: bool
    report_ready: bool
    export_ready: bool
    export_verified: bool
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CanonicalReasonArtifactBundle:
    schema_version: str
    source_contract: str
    canonical_reason_artifacts: List[CanonicalReasonArtifact]
    total_artifacts: int
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_contract": self.source_contract,
            "canonical_reason_artifacts": [item.to_dict() for item in self.canonical_reason_artifacts],
            "total_artifacts": self.total_artifacts,
            "payload_hash": self.payload_hash,
        }


def load_reason_outputs(path: Path) -> List[Dict[str, object]]:
    if path.suffix == ".jsonl":
        rows = _read_jsonl(path)
    else:
        payload = _read_json(path)
        if isinstance(payload.get("results"), list):
            rows = [row for row in payload["results"] if isinstance(row, dict)]
        elif isinstance(payload.get("artifacts"), list):
            rows = [row for row in payload["artifacts"] if isinstance(row, dict)]
        elif isinstance(payload, list):
            rows = [row for row in payload if isinstance(row, dict)]
        else:
            rows = []
    rows.sort(key=lambda row: str(row.get("job_id") or row.get("audit_id") or ""))
    return rows


def _normalize_decision(value: object) -> str:
    normalized = str(value or "BLOCKED").upper()
    allowed = {"APPROVED", "CONDITIONALLY_APPROVED", "BLOCKED"}
    return normalized if normalized in allowed else "BLOCKED"


def _validate_required_string(raw: Dict[str, object], field_name: str) -> str:
    value = str(raw.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"reason output missing required field: {field_name}")
    return value


def _derive_blocking_reasons(
    *,
    deployment_decision: str,
    findings_count: int,
    missing_controls_count: int,
    missing_evidence_count: int,
    review_complete: bool,
    report_ready: bool,
    export_ready: bool,
    export_verified: bool,
    raw_blocking_reasons: List[str],
) -> List[str]:
    blocking = list(raw_blocking_reasons)

    if missing_controls_count > 0:
        blocking.append(f"controls:missing:{missing_controls_count}")
    if missing_evidence_count > 0:
        blocking.append(f"evidence:missing:{missing_evidence_count}")
    if not review_complete:
        blocking.append("review:incomplete")
    if not report_ready:
        blocking.append("report_surface:report_not_ready")
    if not export_ready:
        blocking.append("export_surface:export_not_ready")
    if not export_verified:
        blocking.append("export_surface:export_not_verified")
    if deployment_decision == "BLOCKED":
        blocking.append("deterministic_decision:blocked")
    if findings_count < 0:
        blocking.append("findings:invalid_negative_count")

    return sorted(dict.fromkeys(blocking))


def canonicalize_reason_output(raw: Dict[str, object]) -> CanonicalReasonArtifact:
    job_id = _validate_required_string(raw, "job_id") if raw.get("job_id") else _validate_required_string(raw, "audit_id")
    audit_id = str(raw.get("audit_id") or job_id)
    tenant_id = _validate_required_string(raw, "tenant_id")
    audit_kind = _validate_required_string(raw, "audit_kind")
    schedule_id = str(raw["schedule_id"]) if raw.get("schedule_id") is not None else None

    deployment_decision = _normalize_decision(
        raw.get("deployment_decision") or raw.get("deterministic_decision")
    )

    findings_count = int(raw.get("findings_count", _count_list(raw.get("findings"))))
    missing_controls_count = int(raw.get("missing_controls_count", _count_list(raw.get("missing_controls"))))
    missing_evidence_count = int(raw.get("missing_evidence_count", _count_list(raw.get("missing_evidence"))))
    review_complete = bool(raw.get("review_complete", False))
    report_ready = bool(raw.get("report_ready", False))
    export_ready = bool(raw.get("export_ready", False))
    export_verified = bool(raw.get("export_verified", False))
    raw_blocking_reasons = [str(x) for x in raw.get("blocking_reasons", [])]

    blocking_reasons = _derive_blocking_reasons(
        deployment_decision=deployment_decision,
        findings_count=findings_count,
        missing_controls_count=missing_controls_count,
        missing_evidence_count=missing_evidence_count,
        review_complete=review_complete,
        report_ready=report_ready,
        export_ready=export_ready,
        export_verified=export_verified,
        raw_blocking_reasons=raw_blocking_reasons,
    )

    payload = {
        "job_id": job_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "audit_kind": audit_kind,
        "schedule_id": schedule_id,
        "deployment_decision": deployment_decision,
        "findings_count": findings_count,
        "missing_controls_count": missing_controls_count,
        "missing_evidence_count": missing_evidence_count,
        "review_complete": review_complete,
        "report_ready": report_ready,
        "export_ready": export_ready,
        "export_verified": export_verified,
        "blocking_reasons": blocking_reasons,
    }

    return CanonicalReasonArtifact(
        job_id=payload["job_id"],
        audit_id=payload["audit_id"],
        tenant_id=payload["tenant_id"],
        audit_kind=payload["audit_kind"],
        schedule_id=payload["schedule_id"],
        deployment_decision=payload["deployment_decision"],
        findings_count=payload["findings_count"],
        missing_controls_count=payload["missing_controls_count"],
        missing_evidence_count=payload["missing_evidence_count"],
        review_complete=payload["review_complete"],
        report_ready=payload["report_ready"],
        export_ready=payload["export_ready"],
        export_verified=payload["export_verified"],
        blocking_reasons=payload["blocking_reasons"],
        payload_hash=_stable_json_hash(payload),
    )


def build_canonical_reason_artifact_bundle(raw_outputs: Iterable[Dict[str, object]]) -> CanonicalReasonArtifactBundle:
    artifacts = [canonicalize_reason_output(row) for row in raw_outputs]
    artifacts.sort(key=lambda item: item.job_id)

    payload = {
        "schema_version": REASON_OUTPUT_BRIDGE_SCHEMA_VERSION,
        "source_contract": "reason_output_v1_to_canonical_reason_artifact_v1",
        "canonical_reason_artifacts": [item.to_dict() for item in artifacts],
        "total_artifacts": len(artifacts),
    }

    return CanonicalReasonArtifactBundle(
        schema_version=payload["schema_version"],
        source_contract=payload["source_contract"],
        canonical_reason_artifacts=artifacts,
        total_artifacts=payload["total_artifacts"],
        payload_hash=_stable_json_hash(payload),
    )


def write_canonical_reason_artifact_bundle(path: Path, bundle: CanonicalReasonArtifactBundle) -> None:
    _write_json(path, bundle.to_dict())
