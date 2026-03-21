import json
from pathlib import Path

from src.reasoning.reason import reason
from src.core.pack_runtime import build_runtime_retrieval_inputs, enrich_audit_plan_with_packs
from src.reasoning.audit_plan import build_audit_plan


def _load_case(case_id: str):
    return json.loads(Path(f"evals/gold_cases/{case_id}/audit_context.json").read_text(encoding="utf-8"))


def test_fraud_readiness_review_us():
    ctx = _load_case("fraud_us_monitoring_partial")
    ctx["audit_type"] = "fraud_readiness_review"
    ctx["jurisdictions"] = ["US"]
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)
    assert "fraud" in prep["domains"]
    assert "AML-003" in prep["controls"]
    assert "BSA_AML" in prep["regimes"]
    out = reason(ctx, reasoner=None, runtime_config={
        "enable_model_reasoning": False,
        "model_overlay_sections": [],
        "fallback_to_deterministic_on_model_error": True,
        "require_retrieved_chunks_for_model_reasoning": True,
    })
    assert "deployment_decision" in out


def test_transaction_screening_review_eu():
    ctx = _load_case("screening_eu_quality_checks_gap")
    ctx["audit_type"] = "transaction_screening_review"
    ctx["jurisdictions"] = ["EU"]
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)
    assert "transaction_screening" in prep["domains"]
    assert "SAN-001" in prep["controls"]
    assert "EU_SANCTIONS" in prep["regimes"]
    out = reason(ctx, reasoner=None, runtime_config={
        "enable_model_reasoning": False,
        "model_overlay_sections": [],
        "fallback_to_deterministic_on_model_error": True,
        "require_retrieved_chunks_for_model_reasoning": True,
    })
    assert "control_assessment" in out


def test_regulatory_licensing_readiness_review_uae():
    ctx = _load_case("licensing_uae_vendor_readiness")
    ctx["audit_type"] = "regulatory_licensing_readiness_review"
    ctx["jurisdictions"] = ["UAE"]
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)
    assert "regulatory_licensing" in prep["domains"]
    assert "GOV-001" in prep["controls"]
    assert "UAE_GOVERNANCE_BASELINE" in prep["regimes"]
    out = reason(ctx, reasoner=None, runtime_config={
        "enable_model_reasoning": False,
        "model_overlay_sections": [],
        "fallback_to_deterministic_on_model_error": True,
        "require_retrieved_chunks_for_model_reasoning": True,
    })
    assert "findings" in out


def test_remediation_tracking_review_canada():
    ctx = _load_case("remediation_canada_closure_partial")
    ctx["audit_type"] = "remediation_tracking_review"
    ctx["jurisdictions"] = ["CANADA"]
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)
    assert "remediation_tracking" in prep["domains"]
    assert "VEN-001" in prep["controls"] or "GOV-001" in prep["controls"]
    assert "CA_GOVERNANCE_BASELINE" in prep["regimes"]
    out = reason(ctx, reasoner=None, runtime_config={
        "enable_model_reasoning": False,
        "model_overlay_sections": [],
        "fallback_to_deterministic_on_model_error": True,
        "require_retrieved_chunks_for_model_reasoning": True,
    })
    assert "deployment_decision" in out
