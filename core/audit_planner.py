from __future__ import annotations

from typing import Any

from core.control_library import LibraryControl, build_default_control_library
from core.evidence_pack_service import DEFAULT_PACK_ROOT, get_evidence_pack


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


def normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _match_any(scope_values: set[str], rule_values: list[str]) -> bool:
    return bool(scope_values.intersection({normalize_token(x) for x in rule_values}))


def control_applies(
    *,
    control: LibraryControl,
    domains: list[str],
    jurisdictions: list[str],
    framework_ids: list[str],
    entity_types: list[str],
    product_tags: list[str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    domain_match = _match_any({normalize_token(x) for x in domains}, control.applicability.domains)
    reasons.append("domain_match" if domain_match else "domain_mismatch")

    jurisdiction_match = _match_any({normalize_token(x) for x in jurisdictions}, control.applicability.jurisdictions)
    reasons.append("jurisdiction_match" if jurisdiction_match else "jurisdiction_mismatch")

    framework_match = _match_any({normalize_token(x) for x in framework_ids}, control.applicability.framework_ids)
    reasons.append("framework_match" if framework_match else "framework_mismatch")

    entity_match = _match_any({normalize_token(x) for x in entity_types}, control.applicability.entity_types)
    reasons.append("entity_match" if entity_match else "entity_mismatch")

    product_match = _match_any({normalize_token(x) for x in product_tags}, control.applicability.product_tags)
    reasons.append("product_match" if product_match else "product_mismatch")

    applies = domain_match and jurisdiction_match and framework_match and entity_match and product_match
    return applies, reasons


def build_audit_plan_from_scope(
    *,
    company_profile: dict[str, Any],
    scope: dict[str, Any],
    control_library: list[LibraryControl] | None = None,
) -> dict[str, Any]:
    company_profile = _require_dict(company_profile, "company_profile")
    scope = _require_dict(scope, "scope")
    control_library = control_library or build_default_control_library()

    domains = [normalize_token(str(x)) for x in _require_list(scope.get("domains"), "scope.domains")]
    jurisdictions = [normalize_token(str(x)) for x in _require_list(scope.get("jurisdictions"), "scope.jurisdictions")]
    framework_ids = [normalize_token(str(x)) for x in _require_list(scope.get("framework_ids"), "scope.framework_ids")]
    products = [normalize_token(str(x)) for x in _require_list(company_profile.get("products"), "company_profile.products")]

    entity_types = ["regulated_entity"]
    industry = normalize_token(str(company_profile.get("industry", "")))
    if industry:
        entity_types.append(industry)

    selected_controls = []
    excluded_controls = []

    for control in control_library:
        applies, reasons = control_applies(
            control=control,
            domains=domains,
            jurisdictions=jurisdictions,
            framework_ids=framework_ids,
            entity_types=entity_types,
            product_tags=products,
        )
        row = {
            "control_id": control.control_id,
            "regime_id": control.regime_id,
            "framework_id": control.framework_id,
            "domain": control.domain,
            "title": control.title,
            "required_evidence_types": control.required_evidence_types,
            "severity_if_missing": control.severity_if_missing,
            "match_reasons": reasons,
        }
        if applies:
            selected_controls.append(row)
        else:
            excluded_controls.append(row)

    selected_controls.sort(key=lambda row: (row["framework_id"], row["control_id"]))
    excluded_controls.sort(key=lambda row: (row["framework_id"], row["control_id"]))

    return {
        "company_name": company_profile.get("company_name"),
        "audit_type": scope.get("audit_type"),
        "domains": scope.get("domains"),
        "jurisdictions": scope.get("jurisdictions"),
        "framework_ids": scope.get("framework_ids"),
        "selected_control_count": len(selected_controls),
        "excluded_control_count": len(excluded_controls),
        "selected_controls": selected_controls,
        "excluded_controls": excluded_controls,
    }


def build_audit_plan_from_pack(pack_id: str, pack_root=DEFAULT_PACK_ROOT) -> dict[str, Any]:
    loaded = get_evidence_pack(pack_id, pack_root=pack_root)
    manifest = loaded["manifest"]
    detail = loaded["detail"]

    plan = build_audit_plan_from_scope(
        company_profile=manifest["company_profile"],
        scope=manifest["scope"],
    )
    plan["pack_id"] = detail["pack_id"]
    plan["pack_name"] = detail["name"]
    return plan


def synthesize_controls_for_execution(plan: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    selected_controls = _require_list(plan.get("selected_controls"), "plan.selected_controls")
    evidence_catalog = _require_list(manifest.get("evidence_catalog"), "manifest.evidence_catalog")

    evidence_by_type: dict[str, list[dict[str, Any]]] = {}
    for row in evidence_catalog:
        row = _require_dict(row, "manifest.evidence_catalog[]")
        source_type = normalize_token(str(row.get("source_type", "")))
        if source_type:
            evidence_by_type.setdefault(source_type, []).append(row)

    execution_controls = []
    for row in selected_controls:
        required = [normalize_token(str(x)) for x in row["required_evidence_types"]]
        provided: list[dict[str, Any]] = []
        for evidence_type in required:
            provided.extend(evidence_by_type.get(evidence_type, []))

        execution_controls.append(
            {
                "control": {
                    "control_id": row["control_id"],
                    "regime_id": row["regime_id"],
                    "title": row["title"],
                    "description": f"Planned from deterministic control library for {row['framework_id']}.",
                    "test_procedure": f"Deterministically test required evidence for {row['control_id']}.",
                    "required_evidence_types": row["required_evidence_types"],
                    "severity_if_missing": row["severity_if_missing"],
                },
                "provided_evidence": provided,
                "declared_control_present": True,
                "declared_operating_effective": True,
                "notes": f"Auto-planned from reusable control library. Match reasons: {', '.join(row['match_reasons'])}",
            }
        )

    return execution_controls


def build_execution_payload_from_pack(pack_id: str, pack_root=DEFAULT_PACK_ROOT) -> dict[str, Any]:
    loaded = get_evidence_pack(pack_id, pack_root=pack_root)
    manifest = loaded["manifest"]
    detail = loaded["detail"]

    plan = build_audit_plan_from_scope(
        company_profile=manifest["company_profile"],
        scope=manifest["scope"],
    )
    controls = synthesize_controls_for_execution(plan, manifest)

    return {
        "run_id": "",
        "company_profile": manifest["company_profile"],
        "scope": manifest["scope"],
        "controls": controls,
        "default_remediation_owner": "",
        "prior_historical_context": manifest.get("prior_historical_context", {}),
        "metadata": {
            **manifest.get("metadata", {}),
            "evidence_pack_id": detail["pack_id"],
            "evidence_pack_name": detail["name"],
            "planned_control_count": len(plan["selected_controls"]),
        },
    }
