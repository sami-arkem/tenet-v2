from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


REMEDIATION_TRACKING_SCHEMA_VERSION = "1.0"


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
    content = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True)
class RemediationItem:
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
    release_blocking: bool
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationIndex:
    schema_version: str
    total_items: int
    total_open: int
    total_in_progress: int
    total_resolved: int
    total_release_blocking: int
    severity_counts: Dict[str, int]
    tenant_counts: Dict[str, int]
    audit_kind_counts: Dict[str, int]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationReadinessGate:
    schema_version: str
    gate_name: str
    gate_status: str
    remediation_ready: bool
    total_open_items: int
    total_release_blocking_items: int
    unresolved_release_blockers: List[str]
    blocking_reasons: List[str]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationTrackingState:
    emitted_remediation_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "emitted_remediation_ids": sorted(set(self.emitted_remediation_ids)),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "RemediationTrackingState":
        return cls(
            emitted_remediation_ids=[str(x) for x in payload.get("emitted_remediation_ids", [])],
        )


@dataclass(frozen=True)
class RemediationTrackingResult:
    schema_version: str
    created_items: List[RemediationItem] = field(default_factory=list)
    remediation_index: Optional[RemediationIndex] = None
    remediation_gate: Optional[RemediationReadinessGate] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "created_items": [item.to_dict() for item in self.created_items],
            "remediation_index": self.remediation_index.to_dict() if self.remediation_index is not None else None,
            "remediation_gate": self.remediation_gate.to_dict() if self.remediation_gate is not None else None,
        }


def load_remediation_state(path: Path) -> RemediationTrackingState:
    if not path.exists():
        return RemediationTrackingState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RemediationTrackingState.from_dict(payload)


def save_remediation_state(path: Path, state: RemediationTrackingState) -> None:
    _write_json(path, state.to_dict())


def load_canonical_reason_artifacts(path: Path) -> List[Dict[str, object]]:
    payload = _read_json(path)
    rows = payload.get("canonical_reason_artifacts", [])
    if not isinstance(rows, list):
        return []
    normalized = [row for row in rows if isinstance(row, dict)]
    normalized.sort(key=lambda row: str(row.get("job_id") or row.get("audit_id") or ""))
    return normalized


def load_execution_records(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["schedule_id"], row["due_date"], row["execution_id"]))
    return rows


def load_existing_remediation_items(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))
    return rows


def _severity_for_reason(reason: str) -> str:
    if reason.startswith("deterministic_decision:blocked"):
        return "CRITICAL"
    if reason.startswith("controls:missing:"):
        return "HIGH"
    if reason.startswith("evidence:missing:"):
        return "HIGH"
    if reason.startswith("review:incomplete"):
        return "MEDIUM"
    if reason.startswith("export_surface:"):
        return "HIGH"
    if reason.startswith("report_surface:"):
        return "MEDIUM"
    if reason.startswith("evidence:missing_required_pack"):
        return "HIGH"
    return "MEDIUM"


def _release_blocking_for_reason(reason: str) -> bool:
    return reason.startswith("deterministic_decision:blocked") or reason.startswith("controls:missing:") or reason.startswith("evidence:missing:") or reason.startswith("evidence:missing_required_pack") or reason.startswith("export_surface:")


def _title_for_reason(reason: str) -> str:
    if reason.startswith("deterministic_decision:blocked"):
        return "Deterministic deployment decision is blocked"
    if reason.startswith("controls:missing:"):
        return "Required controls are missing"
    if reason.startswith("evidence:missing:"):
        return "Required evidence is missing"
    if reason.startswith("evidence:missing_required_pack"):
        return "Required evidence pack is missing"
    if reason.startswith("review:incomplete"):
        return "Required review is incomplete"
    if reason.startswith("report_surface:report_not_ready"):
        return "Report is not ready"
    if reason.startswith("export_surface:export_not_ready"):
        return "Export is not ready"
    if reason.startswith("export_surface:export_not_verified"):
        return "Export is not verified"
    return f"Remediate: {reason}"


def _detail_for_reason(reason: str, artifact: Dict[str, object]) -> str:
    return (
        f"Audit {artifact['audit_id']} for tenant {artifact['tenant_id']} "
        f"has unresolved remediation reason: {reason}."
    )


def _remediation_id(artifact: Dict[str, object], source_type: str, source_key: str) -> str:
    return f"{artifact['tenant_id']}:{artifact['audit_kind']}:{artifact['audit_id']}:{source_type}:{source_key}"


def _build_reason_based_items(artifact: Dict[str, object]) -> List[RemediationItem]:
    items: List[RemediationItem] = []
    reasons = [str(x) for x in artifact.get("blocking_reasons", [])]

    for reason in reasons:
        remediation_id = _remediation_id(artifact, "reason", reason)
        severity = _severity_for_reason(reason)
        release_blocking = _release_blocking_for_reason(reason)
        payload = {
            "remediation_id": remediation_id,
            "audit_id": str(artifact["audit_id"]),
            "job_id": str(artifact["job_id"]),
            "tenant_id": str(artifact["tenant_id"]),
            "audit_kind": str(artifact["audit_kind"]),
            "source_type": "reason",
            "source_key": reason,
            "severity": severity,
            "title": _title_for_reason(reason),
            "detail": _detail_for_reason(reason, artifact),
            "status": "OPEN",
            "release_blocking": release_blocking,
        }
        items.append(
            RemediationItem(
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
                release_blocking=payload["release_blocking"],
                payload_hash=_stable_json_hash(payload),
            )
        )

    missing_controls_count = int(artifact.get("missing_controls_count", 0))
    missing_evidence_count = int(artifact.get("missing_evidence_count", 0))

    if missing_controls_count > 0:
        source_key = f"missing_controls_count:{missing_controls_count}"
        remediation_id = _remediation_id(artifact, "derived", source_key)
        payload = {
            "remediation_id": remediation_id,
            "audit_id": str(artifact["audit_id"]),
            "job_id": str(artifact["job_id"]),
            "tenant_id": str(artifact["tenant_id"]),
            "audit_kind": str(artifact["audit_kind"]),
            "source_type": "derived",
            "source_key": source_key,
            "severity": "HIGH",
            "title": "Close missing control gaps",
            "detail": f"Audit {artifact['audit_id']} has {missing_controls_count} missing control(s).",
            "status": "OPEN",
            "release_blocking": True,
        }
        items.append(
            RemediationItem(
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
                release_blocking=payload["release_blocking"],
                payload_hash=_stable_json_hash(payload),
            )
        )

    if missing_evidence_count > 0:
        source_key = f"missing_evidence_count:{missing_evidence_count}"
        remediation_id = _remediation_id(artifact, "derived", source_key)
        payload = {
            "remediation_id": remediation_id,
            "audit_id": str(artifact["audit_id"]),
            "job_id": str(artifact["job_id"]),
            "tenant_id": str(artifact["tenant_id"]),
            "audit_kind": str(artifact["audit_kind"]),
            "source_type": "derived",
            "source_key": source_key,
            "severity": "HIGH",
            "title": "Collect missing evidence",
            "detail": f"Audit {artifact['audit_id']} has {missing_evidence_count} missing evidence item(s).",
            "status": "OPEN",
            "release_blocking": True,
        }
        items.append(
            RemediationItem(
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
                release_blocking=payload["release_blocking"],
                payload_hash=_stable_json_hash(payload),
            )
        )

    return items


def _build_execution_based_items(execution: Dict[str, object]) -> List[RemediationItem]:
    items: List[RemediationItem] = []

    if str(execution.get("execution_status")) in {"BLOCKED", "FAILED"}:
        reasons = [str(x) for x in execution.get("blocking_reasons", [])] or ["deterministic_execution:blocked"]

        for reason in reasons:
            remediation_id = f"{execution['tenant_id']}:{execution['audit_kind']}:{execution['audit_id']}:execution:{reason}"
            payload = {
                "remediation_id": remediation_id,
                "audit_id": str(execution["audit_id"]),
                "job_id": str(execution["job_id"]),
                "tenant_id": str(execution["tenant_id"]),
                "audit_kind": str(execution["audit_kind"]),
                "source_type": "execution",
                "source_key": reason,
                "severity": _severity_for_reason(reason),
                "title": _title_for_reason(reason),
                "detail": f"Execution for audit {execution['audit_id']} is blocked because: {reason}.",
                "status": "OPEN",
                "release_blocking": True,
            }
            items.append(
                RemediationItem(
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
                    release_blocking=payload["release_blocking"],
                    payload_hash=_stable_json_hash(payload),
                )
            )

    return items


def _count_by_key(rows: List[Dict[str, object]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def build_remediation_tracking_outputs(
    *,
    canonical_reason_artifacts: List[Dict[str, object]],
    execution_records: List[Dict[str, object]],
    existing_remediation_items: Optional[List[Dict[str, object]]] = None,
    state: Optional[RemediationTrackingState] = None,
) -> Tuple[RemediationTrackingResult, RemediationTrackingState]:
    current_state = state or RemediationTrackingState()
    existing_rows = existing_remediation_items or []

    emitted_ids: Set[str] = set(current_state.emitted_remediation_ids)
    existing_ids: Set[str] = {str(row["remediation_id"]) for row in existing_rows}

    created_items: List[RemediationItem] = []

    for artifact in canonical_reason_artifacts:
        for item in _build_reason_based_items(artifact):
            if item.remediation_id in emitted_ids or item.remediation_id in existing_ids:
                emitted_ids.add(item.remediation_id)
                existing_ids.add(item.remediation_id)
                continue
            created_items.append(item)
            emitted_ids.add(item.remediation_id)
            existing_ids.add(item.remediation_id)

    for execution in execution_records:
        for item in _build_execution_based_items(execution):
            if item.remediation_id in emitted_ids or item.remediation_id in existing_ids:
                emitted_ids.add(item.remediation_id)
                existing_ids.add(item.remediation_id)
                continue
            created_items.append(item)
            emitted_ids.add(item.remediation_id)
            existing_ids.add(item.remediation_id)

    created_items.sort(key=lambda item: (item.tenant_id, item.audit_kind, item.remediation_id))

    combined_rows: List[Dict[str, object]] = list(existing_rows) + [item.to_dict() for item in created_items]
    combined_rows.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))

    total_items = len(combined_rows)
    total_open = sum(1 for row in combined_rows if str(row.get("status")) == "OPEN")
    total_in_progress = sum(1 for row in combined_rows if str(row.get("status")) == "IN_PROGRESS")
    total_resolved = sum(1 for row in combined_rows if str(row.get("status")) == "RESOLVED")
    total_release_blocking = sum(
        1 for row in combined_rows
        if bool(row.get("release_blocking", False)) and str(row.get("status")) != "RESOLVED"
    )

    index_payload = {
        "schema_version": REMEDIATION_TRACKING_SCHEMA_VERSION,
        "total_items": total_items,
        "total_open": total_open,
        "total_in_progress": total_in_progress,
        "total_resolved": total_resolved,
        "total_release_blocking": total_release_blocking,
        "severity_counts": _count_by_key(combined_rows, "severity") if combined_rows else {},
        "tenant_counts": _count_by_key(combined_rows, "tenant_id") if combined_rows else {},
        "audit_kind_counts": _count_by_key(combined_rows, "audit_kind") if combined_rows else {},
    }
    remediation_index = RemediationIndex(
        schema_version=index_payload["schema_version"],
        total_items=index_payload["total_items"],
        total_open=index_payload["total_open"],
        total_in_progress=index_payload["total_in_progress"],
        total_resolved=index_payload["total_resolved"],
        total_release_blocking=index_payload["total_release_blocking"],
        severity_counts=index_payload["severity_counts"],
        tenant_counts=index_payload["tenant_counts"],
        audit_kind_counts=index_payload["audit_kind_counts"],
        payload_hash=_stable_json_hash(index_payload),
    )

    unresolved_release_blockers = sorted(
        row["remediation_id"]
        for row in combined_rows
        if bool(row.get("release_blocking", False)) and str(row.get("status")) != "RESOLVED"
    )
    blocking_reasons = [f"remediation:unresolved_release_blockers:{len(unresolved_release_blockers)}"] if unresolved_release_blockers else []
    gate_payload = {
        "schema_version": REMEDIATION_TRACKING_SCHEMA_VERSION,
        "gate_name": "remediation_tracking_gate",
        "gate_status": "PASS" if not unresolved_release_blockers else "BLOCKED",
        "remediation_ready": not unresolved_release_blockers,
        "total_open_items": sum(1 for row in combined_rows if str(row.get("status")) != "RESOLVED"),
        "total_release_blocking_items": len(unresolved_release_blockers),
        "unresolved_release_blockers": unresolved_release_blockers,
        "blocking_reasons": blocking_reasons,
    }
    remediation_gate = RemediationReadinessGate(
        schema_version=gate_payload["schema_version"],
        gate_name=gate_payload["gate_name"],
        gate_status=gate_payload["gate_status"],
        remediation_ready=gate_payload["remediation_ready"],
        total_open_items=gate_payload["total_open_items"],
        total_release_blocking_items=gate_payload["total_release_blocking_items"],
        unresolved_release_blockers=gate_payload["unresolved_release_blockers"],
        blocking_reasons=gate_payload["blocking_reasons"],
        payload_hash=_stable_json_hash(gate_payload),
    )

    result = RemediationTrackingResult(
        schema_version=REMEDIATION_TRACKING_SCHEMA_VERSION,
        created_items=created_items,
        remediation_index=remediation_index,
        remediation_gate=remediation_gate,
    )
    next_state = RemediationTrackingState(emitted_remediation_ids=sorted(emitted_ids))
    return result, next_state


def append_remediation_items(*, items: List[RemediationItem], path: Path) -> None:
    existing = _read_jsonl(path)
    seen_ids = {str(row["remediation_id"]) for row in existing}

    for item in items:
        row = item.to_dict()
        if row["remediation_id"] in seen_ids:
            continue
        existing.append(row)
        seen_ids.add(str(row["remediation_id"]))

    existing.sort(key=lambda row: (row["tenant_id"], row["audit_kind"], row["remediation_id"]))
    _write_jsonl(path, existing)


def write_remediation_index(path: Path, artifact: RemediationIndex) -> None:
    _write_json(path, artifact.to_dict())


def write_remediation_gate(path: Path, artifact: RemediationReadinessGate) -> None:
    _write_json(path, artifact.to_dict())
