from __future__ import annotations

from typing import Any, Dict, List

from src.core.constants import AUDIT_TYPES, INDUSTRIES, JURISDICTIONS


REQUIRED_AUDIT_CONTEXT_FIELDS = [
    "audit_type",
    "industry",
    "jurisdictions",
]


def validate_audit_context(audit_context: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    for field in REQUIRED_AUDIT_CONTEXT_FIELDS:
        if field not in audit_context or audit_context[field] in (None, "", []):
            errors.append(f"Missing required field: {field}")

    audit_type = audit_context.get("audit_type")
    if audit_type and audit_type not in AUDIT_TYPES:
        errors.append(f"Invalid audit_type: {audit_type}")

    industry = audit_context.get("industry")
    if industry and industry not in INDUSTRIES:
        errors.append(f"Invalid industry: {industry}")

    jurisdictions = audit_context.get("jurisdictions", [])
    if not isinstance(jurisdictions, list):
        errors.append("jurisdictions must be a list")
    else:
        invalid = [j for j in jurisdictions if j not in JURISDICTIONS]
        if invalid:
            errors.append(f"Invalid jurisdictions: {', '.join(invalid)}")

    return errors
