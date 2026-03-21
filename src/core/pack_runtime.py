from __future__ import annotations

from typing import Any, Dict, List

from src.core.library_loader import load_control_library
from src.core.pack_composer import compose_pack_view
from src.core.retrieval_preparation import build_retrieval_preparation
from src.memory.historical_context import build_historical_context, build_historical_query_terms


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def enrich_audit_plan_with_packs(audit_context: Dict[str, Any], audit_plan: Any) -> Any:
    pack_view = compose_pack_view(audit_context)
    controls_by_id = {
        str(control.get("control_id", "")): control
        for control in load_control_library().get("controls", [])
    }

    existing_regimes = list(getattr(audit_plan, "applicable_regimes", []) or [])
    existing_controls = list(getattr(audit_plan, "required_control_ids", []) or [])
    existing_evidence = list(getattr(audit_plan, "required_evidence_types", []) or [])
    existing_focus = list(getattr(audit_plan, "review_focus", []) or [])

    merged_regimes = _dedupe_keep_order(existing_regimes + pack_view["regimes"])
    merged_controls = _dedupe_keep_order(existing_controls + pack_view["controls"])
    merged_evidence = _dedupe_keep_order(
        existing_evidence
        + [
            str(evidence)
            for control_id in merged_controls
            for evidence in controls_by_id.get(control_id, {}).get("required_evidence", [])
            if evidence
        ]
    )
    merged_focus = _dedupe_keep_order(existing_focus + pack_view["domains"])

    if hasattr(audit_plan, "applicable_regimes"):
        audit_plan.applicable_regimes = merged_regimes
    if hasattr(audit_plan, "required_control_ids"):
        audit_plan.required_control_ids = merged_controls
    if hasattr(audit_plan, "required_evidence_types"):
        audit_plan.required_evidence_types = merged_evidence
    if hasattr(audit_plan, "review_focus"):
        audit_plan.review_focus = merged_focus

    return audit_plan


def build_runtime_retrieval_inputs(audit_context: Dict[str, Any], audit_plan: Any) -> Dict[str, Any]:
    prep = build_retrieval_preparation(audit_context)

    audit_plan_regimes = list(getattr(audit_plan, "applicable_regimes", []) or [])
    audit_plan_controls = list(getattr(audit_plan, "required_control_ids", []) or [])

    entity_name = str(audit_context.get("entity_name", "") or "")
    historical_context = build_historical_context(entity_name)
    historical_query_terms = build_historical_query_terms(historical_context)

    return {
        "audit_type": prep["audit_type"],
        "jurisdictions": prep["jurisdictions"],
        "domains": prep["domains"],
        "regimes": _dedupe_keep_order(audit_plan_regimes + prep["regimes"]),
        "controls": _dedupe_keep_order(audit_plan_controls + prep["controls"]),
        "evidence_categories": prep["evidence_categories"],
        "query_terms": _dedupe_keep_order(prep["query_terms"] + historical_query_terms),
        "historical_context": historical_context,
    }


def build_runtime_retrieval_query(audit_context: Dict[str, Any], audit_plan: Any) -> str:
    runtime = build_runtime_retrieval_inputs(audit_context, audit_plan)

    parts: List[str] = []
    for key in ["audit_type"]:
        value = runtime.get(key)
        if value:
            parts.append(str(value).replace("_", " "))

    for key in ["jurisdictions", "domains", "regimes", "controls", "evidence_categories", "query_terms"]:
        value = runtime.get(key, [])
        if isinstance(value, list):
            parts.extend(str(x).replace("_", " ") for x in value if x)

    return " ".join(_dedupe_keep_order(parts)).strip()
