from dataclasses import dataclass, field

from src.core.pack_runtime import (
    build_runtime_retrieval_inputs,
    build_runtime_retrieval_query,
    enrich_audit_plan_with_packs,
)


@dataclass
class StubAuditPlan:
    applicable_regimes: list[str] = field(default_factory=list)
    required_control_ids: list[str] = field(default_factory=list)
    required_evidence_types: list[str] = field(default_factory=list)
    review_focus: list[str] = field(default_factory=list)


def test_enrich_audit_plan_with_packs_for_aml_us():
    plan = StubAuditPlan(
        applicable_regimes=["BSA_AML"],
        required_control_ids=["AML-001"],
        review_focus=["aml"],
    )
    ctx = {
        "audit_type": "aml_readiness_review",
        "jurisdictions": ["US"],
    }
    enriched = enrich_audit_plan_with_packs(ctx, plan)
    assert "BSA_AML" in enriched.applicable_regimes
    assert "OFAC" in enriched.applicable_regimes
    assert "AML-003" in enriched.required_control_ids
    assert "transaction monitoring procedure" in enriched.required_evidence_types
    assert "kyc_kyb" in enriched.review_focus


def test_build_runtime_retrieval_inputs_for_sanctions_us_eu():
    plan = StubAuditPlan(
        applicable_regimes=["OFAC"],
        required_control_ids=["SAN-001"],
        review_focus=["sanctions"],
    )
    ctx = {
        "audit_type": "sanctions_readiness_review",
        "jurisdictions": ["US", "EU"],
        "query_terms": ["wallet screening"],
    }
    prep = build_runtime_retrieval_inputs(ctx, plan)
    assert "OFAC" in prep["regimes"]
    assert "EU_SANCTIONS" in prep["regimes"]
    assert "screening" in prep["domains"]
    assert "wallet screening" in prep["query_terms"]


def test_build_runtime_retrieval_query_for_vendor_global():
    plan = StubAuditPlan(
        applicable_regimes=["THIRD_PARTY_RISK"],
        required_control_ids=["VEN-001"],
        review_focus=["vendor_risk"],
    )
    ctx = {
        "audit_type": "vendor_internal_compliance_readiness_review",
        "jurisdictions": ["US", "UK", "EU"],
        "query_terms": ["vendor monitoring cadence"],
    }
    query = build_runtime_retrieval_query(ctx, plan)
    assert "vendor monitoring cadence" in query
    assert "THIRD PARTY RISK" in query.upper()
    assert "VEN-001" in query
