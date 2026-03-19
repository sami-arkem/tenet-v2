from src.core.pack_runtime import build_runtime_retrieval_inputs, enrich_audit_plan_with_packs
from src.reasoning.audit_plan import build_audit_plan


def test_runtime_retrieval_inputs_include_historical_context_when_available():
    ctx = {
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_name": "Real AML Case 001",
        "query_terms": ["aml policy"],
    }
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)

    assert "historical_context" in prep
    assert prep["historical_context"]["entity_name"]
    assert isinstance(prep["query_terms"], list)


def test_runtime_retrieval_inputs_do_not_break_without_history():
    ctx = {
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_name": "Definitely Missing Entity",
        "query_terms": ["aml policy"],
    }
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)

    assert prep["historical_context"]["has_history"] is False
    assert "aml policy" in prep["query_terms"]
