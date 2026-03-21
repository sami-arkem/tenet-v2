from src.reasoning.reason import reason


def test_reason_returns_locked_schema_sections():
    result = reason({
        "audit_id": "t-001",
        "entity_name": "Test Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US", "UK"],
        "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
        "query_terms": ["aml", "kyc", "sanctions", "controls"],
        "top_k": 8,
    })
    assert "audit_meta" in result
    assert "deployment_decision" in result
    assert "control_assessment" in result
    assert "confidence_assessment" in result
    assert result["audit_scope"]["audit_type"] == "aml_readiness_review"
