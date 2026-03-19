from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.core.io_utils import atomic_write_json


REMEDIATION_SNAPSHOT_ROOT = Path("data/memory/remediation_snapshots")
REMEDIATION_COMPARISON_ROOT = Path("data/memory/remediation_comparisons")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _entity_dir_name(entity_name: str) -> str:
    return entity_name.lower().replace(" ", "_").replace("/", "_")


def _status_rank(status: str) -> int:
    order = {
        "unknown": 0,
        "open": 1,
        "in_progress": 2,
        "closed": 3,
    }
    return order.get(status, 0)


def _normalize_audit_memory_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "audit_id": _safe_str(snapshot.get("audit_id", "")) or "unknown_audit",
        "entity_name": _safe_str(snapshot.get("entity_name", "")) or "Unknown Entity",
        "audit_type": _safe_str(snapshot.get("audit_type", "")),
        "jurisdictions": list(snapshot.get("jurisdictions", []) or []),
        "domains": list(snapshot.get("domains", []) or []),
        "deployment_decision": snapshot.get("deployment_decision", {}) or {},
        "findings_control_ids": list(snapshot.get("findings_control_ids", []) or []),
        "missing_controls_control_ids": list(snapshot.get("missing_controls_control_ids", []) or []),
        "missing_evidence_refs": list(snapshot.get("missing_evidence_refs", []) or []),
        "remediation_roadmap_summary": snapshot.get("remediation_roadmap_summary", {}) or {},
    }


def build_remediation_snapshot_from_audit_memory(audit_memory_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_audit_memory_snapshot(audit_memory_snapshot)

    findings = set(_dedupe_keep_order(normalized["findings_control_ids"]))
    gaps = set(_dedupe_keep_order(normalized["missing_controls_control_ids"]))
    relevant_controls = _dedupe_keep_order(list(findings | gaps))

    remediation_status_by_control: Dict[str, Dict[str, Any]] = {}
    for control_id in relevant_controls:
        if control_id in gaps:
            status = "open"
            rationale = "Control still appears in missing_controls."
        elif control_id in findings:
            status = "in_progress"
            rationale = "Control still appears in findings but not in missing_controls."
        else:
            status = "unknown"
            rationale = "No deterministic remediation signal available."

        remediation_status_by_control[control_id] = {
            "status": status,
            "rationale": rationale,
        }

    return {
        "snapshot_version": "v1",
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_id": normalized["audit_id"],
        "entity_name": normalized["entity_name"],
        "audit_type": normalized["audit_type"],
        "jurisdictions": normalized["jurisdictions"],
        "domains": normalized["domains"],
        "deployment_decision": normalized["deployment_decision"],
        "remediation_status_by_control": remediation_status_by_control,
        "remediation_roadmap_summary": normalized["remediation_roadmap_summary"],
    }


def write_remediation_snapshot(remediation_snapshot: Dict[str, Any]) -> Path:
    entity_name = _safe_str(remediation_snapshot.get("entity_name", "")) or "Unknown Entity"
    audit_id = _safe_str(remediation_snapshot.get("audit_id", "")) or "unknown_audit"

    out_dir = REMEDIATION_SNAPSHOT_ROOT / _entity_dir_name(entity_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{audit_id}.json"
    atomic_write_json(out_path, remediation_snapshot)
    return out_path


def load_remediation_snapshot(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing remediation snapshot: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _status_from_snapshot(snapshot: Dict[str, Any], control_id: str) -> str:
    statuses = snapshot.get("remediation_status_by_control", {}) or {}
    control = statuses.get(control_id, {}) or {}
    return _safe_str(control.get("status", "")) or "unknown"


def compare_remediation_snapshots(prior: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    prior_statuses = prior.get("remediation_status_by_control", {}) or {}
    current_statuses = current.get("remediation_status_by_control", {}) or {}

    all_controls = _dedupe_keep_order(list(prior_statuses.keys()) + list(current_statuses.keys()))

    status_changes: List[Dict[str, str]] = []
    newly_closed_controls: List[str] = []
    newly_open_controls: List[str] = []
    still_open_controls: List[str] = []
    improved_controls: List[str] = []
    unchanged_controls: List[str] = []

    for control_id in all_controls:
        prior_status = _status_from_snapshot(prior, control_id)
        raw_current_status = _status_from_snapshot(current, control_id)

        if control_id in current_statuses:
            current_status = raw_current_status
        elif control_id in prior_statuses and prior_status in {"open", "in_progress"}:
            current_status = "closed"
        else:
            current_status = "unknown"

        status_changes.append({
            "control_id": control_id,
            "prior_status": prior_status,
            "current_status": current_status,
        })

        if current_status == "closed" and prior_status in {"open", "in_progress"}:
            newly_closed_controls.append(control_id)
        if current_status == "open" and prior_status != "open":
            newly_open_controls.append(control_id)
        if prior_status == "open" and current_status == "open":
            still_open_controls.append(control_id)
        if _status_rank(current_status) > _status_rank(prior_status):
            improved_controls.append(control_id)
        if current_status == prior_status:
            unchanged_controls.append(control_id)

    return {
        "comparison_version": "v1",
        "compared_at_utc": datetime.now(timezone.utc).isoformat(),
        "entity_name": _safe_str(current.get("entity_name", "")) or _safe_str(prior.get("entity_name", "")),
        "prior_audit_id": _safe_str(prior.get("audit_id", "")),
        "current_audit_id": _safe_str(current.get("audit_id", "")),
        "prior_decision": _safe_str((prior.get("deployment_decision", {}) or {}).get("status", "")),
        "current_decision": _safe_str((current.get("deployment_decision", {}) or {}).get("status", "")),
        "status_changes": status_changes,
        "newly_closed_controls": sorted(_dedupe_keep_order(newly_closed_controls)),
        "newly_open_controls": sorted(_dedupe_keep_order(newly_open_controls)),
        "still_open_controls": sorted(_dedupe_keep_order(still_open_controls)),
        "improved_controls": sorted(_dedupe_keep_order(improved_controls)),
        "unchanged_controls": sorted(_dedupe_keep_order(unchanged_controls)),
    }


def write_remediation_comparison(prior: Dict[str, Any], current: Dict[str, Any]) -> Path:
    comparison = compare_remediation_snapshots(prior, current)
    entity_name = _safe_str(comparison.get("entity_name", "")) or "Unknown Entity"
    out_dir = REMEDIATION_COMPARISON_ROOT / _entity_dir_name(entity_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{comparison["prior_audit_id"]}__to__{comparison["current_audit_id"]}.json'
    atomic_write_json(out_path, comparison)
    return out_path
