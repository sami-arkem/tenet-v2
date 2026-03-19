from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from src.core.contracts import validate_audit_context
from src.core.library_loader import (
    control_ids_for_audit_type,
    load_control_library as load_control_library_v2,
    regime_ids_for_audit_type_and_jurisdictions,
)


@dataclass
class AuditPlan:
    audit_type: str
    industry: str
    jurisdictions: List[str]
    applicable_regimes: List[str]
    required_control_ids: List[str]
    required_evidence_types: List[str]
    review_focus: List[str]
    decision_sensitivity: str


def load_control_library() -> List[Dict[str, Any]]:
    return list(load_control_library_v2().get("controls", []))


def select_regimes(audit_type: str, jurisdictions: List[str]) -> List[str]:
    return regime_ids_for_audit_type_and_jurisdictions(audit_type, jurisdictions)


def _normalize_control(control: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "control_id": control.get("control_id", ""),
        "title": control.get("control_name", ""),
        "domain": control.get("category", ""),
        "required_evidence": list(control.get("required_evidence", [])),
        "severity_if_missing": control.get("severity_if_missing", "low"),
    }


def build_audit_plan(audit_context: Dict[str, Any]) -> AuditPlan:
    errors = validate_audit_context(audit_context)
    if errors:
        raise ValueError("Invalid audit_context: " + " | ".join(errors))

    audit_type = audit_context["audit_type"]
    industry = audit_context["industry"]
    jurisdictions = audit_context["jurisdictions"]

    library = [_normalize_control(item) for item in load_control_library()]
    applicable_regimes = select_regimes(audit_type, jurisdictions)
    mapped_control_ids = set(control_ids_for_audit_type(audit_type))

    selected_controls: List[Dict[str, Any]] = []
    for control in library:
        if control.get("control_id") not in mapped_control_ids:
            continue
        selected_controls.append(control)

    required_control_ids = sorted({c["control_id"] for c in selected_controls})
    required_evidence_types = sorted({
        evidence
        for control in selected_controls
        for evidence in control.get("required_evidence", [])
    })
    review_focus = sorted({control.get("domain", "") for control in selected_controls if control.get("domain")})

    decision_sensitivity = "critical" if audit_type in {
        "aml_readiness_review",
        "sanctions_readiness_review",
    } else "high"

    return AuditPlan(
        audit_type=audit_type,
        industry=industry,
        jurisdictions=jurisdictions,
        applicable_regimes=applicable_regimes,
        required_control_ids=required_control_ids,
        required_evidence_types=required_evidence_types,
        review_focus=review_focus,
        decision_sensitivity=decision_sensitivity,
    )


def audit_plan_to_dict(plan: AuditPlan) -> Dict[str, Any]:
    return asdict(plan)
