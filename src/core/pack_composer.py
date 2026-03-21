from __future__ import annotations

from typing import Any, Dict, List

from src.core.library_loader import regime_ids_for_audit_type_and_jurisdictions
from src.core.pack_loader import (
    composed_control_ids,
    load_domain_packs,
    load_jurisdiction_packs,
    query_seeds_for_domain,
    supported_domains_for_jurisdiction,
)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _domain_list_for_audit_context(audit_context: Dict[str, Any]) -> List[str]:
    explicit = audit_context.get("domains", [])
    if explicit:
        return _dedupe_keep_order([str(x) for x in explicit if x])

    audit_type = str(audit_context.get("audit_type", "") or "")
    mapping = {
        "aml_readiness_review": ["aml", "kyc_kyb", "sanctions", "governance"],
        "kyc_kyb_policy_and_control_review": ["kyc_kyb", "governance"],
        "sanctions_readiness_review": ["sanctions", "screening", "governance"],
        "policy_governance_gap_analysis": ["governance", "vendor_risk"],
        "vendor_internal_compliance_readiness_review": ["vendor_risk", "governance"],
        "fraud_readiness_review": ["fraud", "governance"],
        "transaction_screening_review": ["transaction_screening", "sanctions", "governance"],
        "regulatory_licensing_readiness_review": ["regulatory_licensing", "governance"],
        "remediation_tracking_review": ["remediation_tracking", "governance"],
        "audit_report_generation_from_uploaded_evidence": ["aml", "kyc_kyb", "sanctions", "governance", "vendor_risk"],
    }
    return mapping.get(audit_type, ["governance"])


def compose_pack_view(audit_context: Dict[str, Any]) -> Dict[str, Any]:
    jurisdictions = _dedupe_keep_order([str(x).upper() for x in audit_context.get("jurisdictions", []) if x])
    domains = _domain_list_for_audit_context(audit_context)

    jurisdiction_packs = load_jurisdiction_packs()
    domain_packs = load_domain_packs()

    allowed_domains: List[str] = []
    if jurisdictions:
        for jurisdiction in jurisdictions:
            allowed_domains.extend(supported_domains_for_jurisdiction(jurisdiction))
        allowed_domains = _dedupe_keep_order(allowed_domains)
    else:
        allowed_domains = list(domain_packs.keys())

    resolved_domains = [d for d in domains if d in allowed_domains]
    resolved_domains = _dedupe_keep_order(resolved_domains)

    mapped_regimes = regime_ids_for_audit_type_and_jurisdictions(
        str(audit_context.get("audit_type", "") or ""),
        jurisdictions,
    )
    fallback_regimes: List[str] = []
    if not mapped_regimes:
        for jurisdiction in jurisdictions:
            pack = jurisdiction_packs.get(jurisdiction, {})
            fallback_regimes.extend(pack.get("regimes", []))

    controls = composed_control_ids(resolved_domains)

    evidence_categories: List[str] = []
    query_seeds: List[str] = []

    for domain in resolved_domains:
        pack = domain_packs.get(domain, {})
        evidence_categories.extend(pack.get("evidence_categories", []))
        query_seeds.extend(query_seeds_for_domain(domain))

    return {
        "jurisdictions": jurisdictions,
        "domains": resolved_domains,
        "regimes": _dedupe_keep_order(mapped_regimes + fallback_regimes),
        "controls": _dedupe_keep_order(controls),
        "evidence_categories": _dedupe_keep_order(evidence_categories),
        "query_seeds": _dedupe_keep_order(query_seeds),
        "jurisdiction_pack_ids": _dedupe_keep_order([
            jurisdiction_packs[j]["pack_id"] for j in jurisdictions if j in jurisdiction_packs
        ]),
        "domain_pack_ids": _dedupe_keep_order([
            domain_packs[d]["pack_id"] for d in resolved_domains if d in domain_packs
        ]),
    }
