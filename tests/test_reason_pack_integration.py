from src.reasoning.reason import reason


def test_reason_runs_with_pack_integration_aml_us():
    out = reason(
        audit_context={
            "audit_id": "pack-int-001",
            "entity_name": "Pack Integration Entity",
            "audit_type": "aml_readiness_review",
            "industry": "fintech",
            "jurisdictions": ["US"],
            "source_families": ["regulations", "aml"],
            "query_terms": ["aml policy"],
            "top_k": 2,
        },
        reasoner=None,
        runtime_config={
            "enable_model_reasoning": False,
            "model_overlay_sections": [],
            "fallback_to_deterministic_on_model_error": True,
            "require_retrieved_chunks_for_model_reasoning": True
        }
    )
    assert "deployment_decision" in out
    assert "control_assessment" in out
    assert out["audit_scope"]["audit_type"] == "aml_readiness_review"
