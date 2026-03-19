from src.reasoning.audit_plan import build_audit_plan


def test_build_audit_plan_for_aml_fintech():
    plan = build_audit_plan({
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US", "UK"],
    })
    assert plan.audit_type == "aml_readiness_review"
    assert "BSA_AML" in plan.applicable_regimes
    assert "UK_MLR" in plan.applicable_regimes
    assert len(plan.required_control_ids) > 0
