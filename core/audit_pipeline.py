from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core.audit_runtime import (
    AuditScope,
    CompanyProfile,
    ControlDefinition,
    ControlInput,
    DeploymentDecision,
    DeterministicAuditResult,
    EvidenceReference,
    FindingSeverity,
    build_report_pack,
    run_deterministic_audit,
)


SEVERITY_MAP = {
    "CRITICAL": FindingSeverity.CRITICAL,
    "HIGH": FindingSeverity.HIGH,
    "MEDIUM": FindingSeverity.MEDIUM,
    "LOW": FindingSeverity.LOW,
}


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


def _require_non_empty_string_list(value: Any, field_name: str) -> list[str]:
    values = [str(x).strip() for x in _require_list(value, field_name)]
    if not values or not all(values):
        raise ValueError(f"{field_name} must be a non-empty list of non-empty strings")
    return values


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def parse_company_profile(payload: dict[str, Any]) -> CompanyProfile:
    payload = _require_dict(payload, "company_profile")
    return CompanyProfile(
        company_name=_require_non_empty_str(payload.get("company_name"), "company_profile.company_name"),
        industry=_require_non_empty_str(payload.get("industry"), "company_profile.industry"),
        primary_jurisdiction=_require_non_empty_str(payload.get("primary_jurisdiction"), "company_profile.primary_jurisdiction"),
        additional_jurisdictions=[str(x).strip() for x in _require_list(payload.get("additional_jurisdictions", []), "company_profile.additional_jurisdictions")],
        products=[str(x).strip() for x in _require_list(payload.get("products", []), "company_profile.products")],
        entities=[str(x).strip() for x in _require_list(payload.get("entities", []), "company_profile.entities")],
    )


def parse_scope(payload: dict[str, Any]) -> AuditScope:
    payload = _require_dict(payload, "scope")
    return AuditScope(
        audit_id=_require_non_empty_str(payload.get("audit_id"), "scope.audit_id"),
        audit_type=_require_non_empty_str(payload.get("audit_type"), "scope.audit_type"),
        framework_ids=_require_non_empty_string_list(payload.get("framework_ids"), "scope.framework_ids"),
        domain=_require_non_empty_str(payload.get("domain"), "scope.domain"),
        domains=_require_non_empty_string_list(payload.get("domains"), "scope.domains"),
        jurisdictions=_require_non_empty_string_list(payload.get("jurisdictions"), "scope.jurisdictions"),
        in_scope_entities=_require_non_empty_string_list(payload.get("in_scope_entities"), "scope.in_scope_entities"),
        in_scope_products=_require_non_empty_string_list(payload.get("in_scope_products"), "scope.in_scope_products"),
        evaluation_date=_require_non_empty_str(payload.get("evaluation_date"), "scope.evaluation_date"),
        historical_context_is_non_authoritative=bool(payload.get("historical_context_is_non_authoritative", True)),
        deterministic_current_audit_truth_only=bool(payload.get("deterministic_current_audit_truth_only", True)),
    )


def parse_evidence_list(payload: list[dict[str, Any]]) -> list[EvidenceReference]:
    evidence_refs: list[EvidenceReference] = []
    for idx, row in enumerate(payload):
        row = _require_dict(row, f"evidence[{idx}]")
        evidence_refs.append(
            EvidenceReference(
                evidence_id=_require_non_empty_str(row.get("evidence_id"), f"evidence[{idx}].evidence_id"),
                title=_require_non_empty_str(row.get("title"), f"evidence[{idx}].title"),
                source_type=_require_non_empty_str(row.get("source_type"), f"evidence[{idx}].source_type"),
                file_path=_require_non_empty_str(row.get("file_path"), f"evidence[{idx}].file_path"),
                citation=_require_non_empty_str(row.get("citation"), f"evidence[{idx}].citation"),
                content_hash=str(row["content_hash"]).strip() if row.get("content_hash") else None,
                collected_at=str(row["collected_at"]).strip() if row.get("collected_at") else None,
            )
        )
    return evidence_refs


def parse_control_inputs(payload: list[dict[str, Any]]) -> list[ControlInput]:
    rows = _require_list(payload, "controls")
    control_inputs: list[ControlInput] = []

    for idx, row in enumerate(rows):
        row = _require_dict(row, f"controls[{idx}]")
        control_payload = _require_dict(row.get("control"), f"controls[{idx}].control")
        severity_raw = _require_non_empty_str(control_payload.get("severity_if_missing"), f"controls[{idx}].control.severity_if_missing")
        if severity_raw not in SEVERITY_MAP:
            raise ValueError(f"controls[{idx}].control.severity_if_missing invalid: {severity_raw}")

        evidence_payload = _require_list(row.get("provided_evidence", []), f"controls[{idx}].provided_evidence")
        provided_evidence = parse_evidence_list(evidence_payload)

        control = ControlDefinition(
            control_id=_require_non_empty_str(control_payload.get("control_id"), f"controls[{idx}].control.control_id"),
            regime_id=_require_non_empty_str(control_payload.get("regime_id"), f"controls[{idx}].control.regime_id"),
            title=_require_non_empty_str(control_payload.get("title"), f"controls[{idx}].control.title"),
            description=_require_non_empty_str(control_payload.get("description"), f"controls[{idx}].control.description"),
            test_procedure=_require_non_empty_str(control_payload.get("test_procedure"), f"controls[{idx}].control.test_procedure"),
            required_evidence_types=[str(x).strip() for x in _require_list(control_payload.get("required_evidence_types"), f"controls[{idx}].control.required_evidence_types")],
            severity_if_missing=SEVERITY_MAP[severity_raw],
        )

        declared_control_present = row.get("declared_control_present")
        if not isinstance(declared_control_present, bool):
            raise ValueError(f"controls[{idx}].declared_control_present must be bool")

        declared_operating_effective = row.get("declared_operating_effective")
        if declared_operating_effective is not None and not isinstance(declared_operating_effective, bool):
            raise ValueError(f"controls[{idx}].declared_operating_effective must be bool | null")

        control_inputs.append(
            ControlInput(
                control=control,
                provided_evidence=provided_evidence,
                declared_control_present=declared_control_present,
                declared_operating_effective=declared_operating_effective,
                notes=str(row.get("notes", "")),
            )
        )

    return control_inputs


def run_audit_from_payload(payload: dict[str, Any]) -> DeterministicAuditResult:
    payload = _require_dict(payload, "payload")

    run_id = _require_non_empty_str(payload.get("run_id"), "run_id")
    company_profile = parse_company_profile(payload.get("company_profile"))
    scope = parse_scope(payload.get("scope"))
    control_inputs = parse_control_inputs(payload.get("controls"))
    remediation_owner = _require_non_empty_str(payload.get("default_remediation_owner"), "default_remediation_owner")

    prior_historical_context = payload.get("prior_historical_context", {})
    if not isinstance(prior_historical_context, dict):
        raise ValueError("prior_historical_context must be object")

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be object")

    return run_deterministic_audit(
        run_id=run_id,
        company_profile=company_profile,
        scope=scope,
        control_inputs=control_inputs,
        default_remediation_owner=remediation_owner,
        prior_historical_context=prior_historical_context,
        metadata=metadata,
    )


def build_execution_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    result = run_audit_from_payload(payload)
    report_pack = build_report_pack(result)

    return {
        "deterministic_audit_result": result.to_dict(),
        "report_pack": report_pack,
        "topline": {
            "run_id": result.run_id,
            "overall_posture": result.summary.overall_posture.value,
            "deployment_decision": result.summary.deployment_decision.value,
            "control_count": result.summary.control_count,
            "finding_count": len(result.findings),
            "remediation_item_count": len(result.remediation_items),
        },
    }


def derive_readiness_label(result: DeterministicAuditResult) -> str:
    decision = result.summary.deployment_decision
    if decision == DeploymentDecision.APPROVED:
        return "READY"
    if decision == DeploymentDecision.CONDITIONALLY_APPROVED:
        return "REMEDIATION_REQUIRED"
    return "NOT_READY"


def summarize_findings_by_severity(result: DeterministicAuditResult) -> dict[str, int]:
    counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }
    for finding in result.findings:
        counts[finding.severity.value] += 1
    return counts


def result_to_snapshot(result: DeterministicAuditResult) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "readiness_label": derive_readiness_label(result),
        "summary": asdict(result.summary),
        "finding_counts": summarize_findings_by_severity(result),
        "remediation_items": [asdict(x) for x in result.remediation_items],
    }
