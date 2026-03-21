from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.audit_planner import build_execution_payload_from_pack
from core.evidence_pack_service import DEFAULT_PACK_ROOT, get_evidence_pack
from core.evidence_processing_service import build_corpus_readiness


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


@dataclass(frozen=True)
class ControlReadinessResult:
    control_id: str
    regime_id: str
    title: str
    declared_control_present: bool
    required_evidence_types: list[str]
    provided_evidence_types: list[str]
    missing_evidence_types: list[str]
    readiness_status: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "regime_id": self.regime_id,
            "title": self.title,
            "declared_control_present": self.declared_control_present,
            "required_evidence_types": self.required_evidence_types,
            "provided_evidence_types": self.provided_evidence_types,
            "missing_evidence_types": self.missing_evidence_types,
            "readiness_status": self.readiness_status,
            "rationale": self.rationale,
        }


def evaluate_control_readiness(control_row: dict[str, Any]) -> ControlReadinessResult:
    control_row = _require_dict(control_row, "control_row")
    control = _require_dict(control_row.get("control"), "control_row.control")

    control_id = str(control.get("control_id", "")).strip()
    regime_id = str(control.get("regime_id", "")).strip()
    title = str(control.get("title", "")).strip()
    if not control_id or not regime_id or not title:
        raise ValueError("control_row.control must include control_id, regime_id, and title")

    declared_control_present = control_row.get("declared_control_present")
    if not isinstance(declared_control_present, bool):
        raise ValueError(f"{control_id}: declared_control_present must be bool")

    required_evidence_types = [
        str(x).strip()
        for x in _require_list(control.get("required_evidence_types"), f"{control_id}.required_evidence_types")
        if str(x).strip()
    ]
    if not required_evidence_types:
        raise ValueError(f"{control_id}: required_evidence_types must be non-empty")

    provided_rows = _require_list(control_row.get("provided_evidence", []), f"{control_id}.provided_evidence")
    provided_evidence_types = sorted(
        {
            str(row.get("source_type", "")).strip()
            for row in provided_rows
            if isinstance(row, dict) and str(row.get("source_type", "")).strip()
        }
    )

    required_set = set(required_evidence_types)
    provided_set = set(provided_evidence_types)
    missing_evidence_types = sorted(required_set - provided_set)

    if declared_control_present is False:
        readiness_status = "BLOCKED"
        rationale = "Declared control is absent."
    elif missing_evidence_types and provided_evidence_types:
        readiness_status = "PARTIAL"
        rationale = "Control is present, but evidence coverage is incomplete."
    elif missing_evidence_types:
        readiness_status = "MISSING_EVIDENCE"
        rationale = "No required evidence coverage is present."
    else:
        readiness_status = "READY"
        rationale = "Required evidence coverage is present for this control."

    return ControlReadinessResult(
        control_id=control_id,
        regime_id=regime_id,
        title=title,
        declared_control_present=declared_control_present,
        required_evidence_types=required_evidence_types,
        provided_evidence_types=provided_evidence_types,
        missing_evidence_types=missing_evidence_types,
        readiness_status=readiness_status,
        rationale=rationale,
    )


def summarize_pack_readiness(control_results: list[ControlReadinessResult]) -> dict[str, Any]:
    if not isinstance(control_results, list):
        raise ValueError("control_results must be list")
    if not control_results:
        return {
            "overall_status": "NO_APPLICABLE_CONTROLS",
            "control_count": 0,
            "ready_controls": 0,
            "partial_controls": 0,
            "missing_evidence_controls": 0,
            "blocked_controls": 0,
            "missing_evidence_by_type": {},
        }

    ready = sum(1 for row in control_results if row.readiness_status == "READY")
    partial = sum(1 for row in control_results if row.readiness_status == "PARTIAL")
    missing = sum(1 for row in control_results if row.readiness_status == "MISSING_EVIDENCE")
    blocked = sum(1 for row in control_results if row.readiness_status == "BLOCKED")

    if blocked > 0:
        overall_status = "NOT_READY"
    elif missing > 0 or partial > 0:
        overall_status = "REMEDIATION_REQUIRED"
    else:
        overall_status = "READY"

    missing_evidence_by_type: dict[str, int] = {}
    for row in control_results:
        for value in row.missing_evidence_types:
            missing_evidence_by_type[value] = missing_evidence_by_type.get(value, 0) + 1

    return {
        "overall_status": overall_status,
        "control_count": len(control_results),
        "ready_controls": ready,
        "partial_controls": partial,
        "missing_evidence_controls": missing,
        "blocked_controls": blocked,
        "missing_evidence_by_type": dict(sorted(missing_evidence_by_type.items())),
    }


def build_readiness_plan(pack_id: str, pack_root=DEFAULT_PACK_ROOT) -> dict[str, Any]:
    loaded = get_evidence_pack(pack_id, pack_root=pack_root)
    detail = loaded["detail"]
    manifest = loaded["manifest"]

    if manifest.get("controls"):
        controls = _require_list(manifest.get("controls"), "manifest.controls")
    else:
        controls = build_execution_payload_from_pack(pack_id, pack_root=pack_root)["controls"]

    control_results = [evaluate_control_readiness(row) for row in controls]
    summary = summarize_pack_readiness(control_results)
    corpus = build_corpus_readiness(pack_id, pack_root=pack_root)

    requested_evidence_actions = []
    for row in control_results:
        if row.missing_evidence_types:
            requested_evidence_actions.append(
                {
                    "control_id": row.control_id,
                    "regime_id": row.regime_id,
                    "title": row.title,
                    "request_evidence_types": row.missing_evidence_types,
                    "reason": row.rationale,
                }
            )

    return {
        "pack_id": detail["pack_id"],
        "pack_name": detail["name"],
        "company_name": detail["manifest_summary"]["company_name"],
        "audit_type": detail["manifest_summary"]["audit_type"],
        "domain": detail["manifest_summary"]["domain"],
        "jurisdictions": detail["manifest_summary"]["jurisdictions"],
        "summary": summary,
        "controls": [row.to_dict() for row in control_results],
        "requested_evidence_actions": requested_evidence_actions,
        "corpus_readiness": corpus,
    }
