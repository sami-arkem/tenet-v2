from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.core.io_utils import atomic_write_json


MEMORY_ROOT = Path("data/memory/snapshots")
COMPARISON_ROOT = Path("data/memory/comparisons")


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_domains(audit_output: Dict[str, Any]) -> List[str]:
    scope = audit_output.get("audit_scope", {}) or {}
    domains = scope.get("domains", []) or []
    if isinstance(domains, list) and domains:
        return _dedupe_keep_order(_safe_str(x) for x in domains if _safe_str(x))

    findings = audit_output.get("findings", []) or []
    inferred = []
    for finding in findings:
        domain = _safe_str((finding or {}).get("domain", ""))
        if domain:
            inferred.append(domain)
    return _dedupe_keep_order(inferred)


def _extract_control_ids(items: List[Dict[str, Any]]) -> List[str]:
    values = []
    for item in items or []:
        control_id = _safe_str((item or {}).get("control_id", ""))
        if control_id:
            values.append(control_id)
    return _dedupe_keep_order(values)


def _extract_missing_evidence_refs(items: List[Dict[str, Any]]) -> List[str]:
    values = []
    for item in items or []:
        control_id = _safe_str((item or {}).get("control_id", ""))
        title = _safe_str((item or {}).get("title", ""))
        values.append(control_id or title)
    return _dedupe_keep_order(x for x in values if x)


def _extract_remediation_summary(audit_output: Dict[str, Any]) -> Dict[str, List[str]]:
    roadmap = audit_output.get("remediation_roadmap", {}) or {}
    return {
        "immediate_0_30_days": list(roadmap.get("immediate_0_30_days", []) or []),
        "near_term_30_90_days": list(roadmap.get("near_term_30_90_days", []) or []),
        "medium_term_90_180_days": list(roadmap.get("medium_term_90_180_days", []) or []),
        "strategic_180_plus_days": list(roadmap.get("strategic_180_plus_days", []) or []),
    }


def build_audit_memory_snapshot(audit_output: Dict[str, Any]) -> Dict[str, Any]:
    audit_meta = audit_output.get("audit_meta", {}) or {}
    entity_profile = audit_output.get("entity_profile", {}) or {}
    decision = audit_output.get("deployment_decision", {}) or {}

    audit_id = _safe_str(audit_meta.get("audit_id", "")) or "unknown_audit"
    entity_name = (
        _safe_str(entity_profile.get("legal_name", ""))
        or _safe_str(entity_profile.get("entity_name", ""))
        or _safe_str(audit_output.get("executive_summary", {}).get("system_or_business_reviewed", ""))
        or "Unknown Entity"
    )

    snapshot = {
        "snapshot_version": "v1",
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_id": audit_id,
        "entity_name": entity_name,
        "audit_type": _safe_str((audit_output.get("audit_scope", {}) or {}).get("audit_type", "")),
        "jurisdictions": list((audit_output.get("audit_scope", {}) or {}).get("jurisdictions", []) or []),
        "domains": _extract_domains(audit_output),
        "deployment_decision": {
            "status": _safe_str(decision.get("status", "")),
            "decision_rationale": _safe_str(decision.get("decision_rationale", "")),
            "blocking_issues": list(decision.get("blocking_issues", []) or []),
        },
        "findings_control_ids": _extract_control_ids(audit_output.get("findings", []) or []),
        "missing_controls_control_ids": _extract_control_ids(audit_output.get("missing_controls", []) or []),
        "missing_evidence_refs": _extract_missing_evidence_refs(audit_output.get("missing_evidence", []) or []),
        "remediation_roadmap_summary": _extract_remediation_summary(audit_output),
    }
    return snapshot


def _entity_dir(entity_name: str) -> Path:
    safe = entity_name.lower().replace(" ", "_").replace("/", "_")
    return MEMORY_ROOT / safe


def write_audit_memory_snapshot(audit_output: Dict[str, Any]) -> Path:
    snapshot = build_audit_memory_snapshot(audit_output)
    out_dir = _entity_dir(snapshot["entity_name"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{snapshot["audit_id"]}.json'
    atomic_write_json(out_path, snapshot)
    return out_path


def load_audit_memory_snapshot(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing snapshot: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compare_audit_memory_snapshots(prior: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    prior_findings = set(prior.get("findings_control_ids", []) or [])
    current_findings = set(current.get("findings_control_ids", []) or [])

    prior_gaps = set(prior.get("missing_controls_control_ids", []) or [])
    current_gaps = set(current.get("missing_controls_control_ids", []) or [])

    comparison = {
        "comparison_version": "v1",
        "compared_at_utc": datetime.now(timezone.utc).isoformat(),
        "entity_name": current.get("entity_name", "") or prior.get("entity_name", ""),
        "prior_audit_id": prior.get("audit_id", ""),
        "current_audit_id": current.get("audit_id", ""),
        "prior_decision": (prior.get("deployment_decision", {}) or {}).get("status", ""),
        "current_decision": (current.get("deployment_decision", {}) or {}).get("status", ""),
        "newly_introduced_gaps": sorted(current_gaps - prior_gaps),
        "closed_gaps": sorted(prior_gaps - current_gaps),
        "unchanged_gaps": sorted(prior_gaps & current_gaps),
        "newly_introduced_findings": sorted(current_findings - prior_findings),
        "closed_findings": sorted(prior_findings - current_findings),
        "unchanged_findings": sorted(prior_findings & current_findings),
    }
    return comparison


def write_audit_memory_comparison(prior: Dict[str, Any], current: Dict[str, Any]) -> Path:
    comparison = compare_audit_memory_snapshots(prior, current)
    entity_name = comparison["entity_name"] or "unknown_entity"
    safe = entity_name.lower().replace(" ", "_").replace("/", "_")
    out_dir = COMPARISON_ROOT / safe
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{comparison["prior_audit_id"]}__to__{comparison["current_audit_id"]}.json'
    atomic_write_json(out_path, comparison)
    return out_path
