from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


TREND_ROOT = Path("data/memory/trends")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _entity_slug(entity_name: str) -> str:
    return entity_name.lower().replace(" ", "_").replace("/", "_")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_trend_summary_for_entity(entity_name: str) -> Optional[Dict[str, Any]]:
    if not entity_name:
        return None
    path = TREND_ROOT / f"{_entity_slug(entity_name)}.json"
    if not path.exists():
        return None
    return _read_json(path)


def build_historical_context(entity_name: str) -> Dict[str, Any]:
    trend = load_trend_summary_for_entity(entity_name)
    if not trend:
        return {
            "has_history": False,
            "entity_name": entity_name,
            "prior_recurring_missing_controls": [],
            "prior_recurring_findings": [],
            "prior_decision_trajectory": {},
            "prior_remediation_trajectory": {},
        }

    recurring_missing = [
        x.get("control_id") or x.get("key")
        for x in trend.get("recurring_missing_controls", []) or []
        if (x.get("control_id") or x.get("key"))
    ]
    recurring_findings = [
        x.get("control_id") or x.get("key")
        for x in trend.get("recurring_findings", []) or []
        if (x.get("control_id") or x.get("key"))
    ]
    audit_count = int(trend.get("audit_count", 0) or 0)
    decision_trajectory = trend.get("decision_trajectory", {}) or {}
    remediation_trajectory = trend.get("remediation_improvement_trajectory", {}) or {}

    if audit_count < 2:
        return {
            "has_history": False,
            "entity_name": _safe_str(trend.get("entity_name", "")) or entity_name,
            "audit_count": audit_count,
            "prior_recurring_missing_controls": [],
            "prior_recurring_findings": [],
            "prior_decision_trajectory": {},
            "prior_remediation_trajectory": {},
            "repeated_governance_weaknesses": [],
            "repeated_screening_weaknesses": [],
            "repeated_licensing_weaknesses": [],
            "repeated_remediation_weaknesses": [],
        }

    return {
        "has_history": True,
        "entity_name": _safe_str(trend.get("entity_name", "")) or entity_name,
        "audit_count": audit_count,
        "prior_recurring_missing_controls": recurring_missing,
        "prior_recurring_findings": recurring_findings,
        "prior_decision_trajectory": decision_trajectory,
        "prior_remediation_trajectory": remediation_trajectory,
        "repeated_governance_weaknesses": [
            x.get("control_id") or x.get("key")
            for x in trend.get("repeated_governance_weaknesses", []) or []
            if (x.get("control_id") or x.get("key"))
        ],
        "repeated_screening_weaknesses": [
            x.get("control_id") or x.get("key")
            for x in trend.get("repeated_screening_weaknesses", []) or []
            if (x.get("control_id") or x.get("key"))
        ],
        "repeated_licensing_weaknesses": [
            x.get("control_id") or x.get("key")
            for x in trend.get("repeated_licensing_weaknesses", []) or []
            if (x.get("control_id") or x.get("key"))
        ],
        "repeated_remediation_weaknesses": [
            x.get("control_id") or x.get("key")
            for x in trend.get("repeated_remediation_weaknesses", []) or []
            if (x.get("control_id") or x.get("key"))
        ],
    }


def build_historical_query_terms(historical_context: Dict[str, Any]) -> List[str]:
    if not historical_context.get("has_history"):
        return []

    terms: List[str] = []

    for control_id in historical_context.get("prior_recurring_missing_controls", [])[:10]:
        terms.append(f"historical missing control {control_id}")

    for control_id in historical_context.get("prior_recurring_findings", [])[:10]:
        terms.append(f"historical finding {control_id}")

    decision_trajectory = historical_context.get("prior_decision_trajectory", {}) or {}
    decision_status = _safe_str(decision_trajectory.get("status", ""))
    latest_decision = _safe_str(decision_trajectory.get("latest_decision", ""))
    if decision_status:
        terms.append(f"historical decision trajectory {decision_status}")
    if latest_decision:
        terms.append(f"latest prior decision {latest_decision}")

    remediation_trajectory = historical_context.get("prior_remediation_trajectory", {}) or {}
    remediation_status = _safe_str(remediation_trajectory.get("status", ""))
    if remediation_status:
        terms.append(f"historical remediation trajectory {remediation_status}")

    for key in [
        "repeated_governance_weaknesses",
        "repeated_screening_weaknesses",
        "repeated_licensing_weaknesses",
        "repeated_remediation_weaknesses",
    ]:
        for control_id in historical_context.get(key, [])[:5]:
            terms.append(f"{key.replace('_', ' ')} {control_id}")

    deduped: List[str] = []
    seen = set()
    for item in terms:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
