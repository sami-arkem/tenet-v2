from src.reasoning.model_reasoner import ModelReasonerResult
from src.reasoning.reason import reason


class StubReasoner:
    def __init__(self, output=None, should_fail=False):
        self.output = output or {}
        self.should_fail = should_fail

    def is_configured(self) -> bool:
        return True

    def reason(self, audit_context, audit_plan, retrieved_chunks, model_name=None):
        if self.should_fail:
            from src.reasoning.model_reasoner import ModelReasonerError
            raise ModelReasonerError("synthetic model failure")
        return ModelReasonerResult(
            output=self.output,
            model_name="gpt-5",
            provider="openai_compatible",
            repaired=False,
            validation_errors=[],
            model_metadata={},
        )


def test_reason_uses_deterministic_fallback_when_model_fails():
    result = reason(
        {
            "audit_id": "t-001",
            "entity_name": "Test Entity",
            "audit_type": "aml_readiness_review",
            "industry": "fintech",
            "jurisdictions": ["US", "UK"],
            "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
            "query_terms": ["aml", "kyc", "sanctions", "controls"],
            "top_k": 8,
        },
        reasoner=StubReasoner(should_fail=True),
        runtime_config={
            "enable_model_reasoning": True,
            "model_overlay_sections": [
                "executive_summary",
                "findings",
                "key_risks",
                "remediation_roadmap",
                "reporting_outputs"
            ],
            "fallback_to_deterministic_on_model_error": True,
            "require_retrieved_chunks_for_model_reasoning": False
        },
    )
    assert result["audit_meta"]["reasoning_mode"] == "deterministic_fallback"
    assert "deployment_decision" in result
    assert "control_assessment" in result


def test_reason_applies_model_overlay_sections_only():
    model_output = {
        "executive_summary": {
            "system_or_business_reviewed": "Model Summary Entity",
            "overall_readiness": "CONDITIONALLY_APPROVED",
            "top_issues": ["Model generated issue"],
            "decision_summary": "Model-generated summary",
            "board_message": "Model-generated board summary"
        },
        "findings": [
            {
                "finding_id": "F-999",
                "title": "Model finding",
                "domain": "policy_governance",
                "severity": "HIGH",
                "status": "PARTIAL",
                "description": "Model-generated finding",
                "citations": [],
                "control_id": "AML-001"
            }
        ],
        "key_risks": [],
        "remediation_roadmap": {
            "immediate_0_30_days": [],
            "near_term_30_90_days": [],
            "medium_term_90_180_days": [],
            "strategic_180_plus_days": []
        },
        "reporting_outputs": {
            "board_ready_summary": "Model board summary",
            "regulator_ready_summary": "Model regulator summary",
            "client_facing_summary": "Model client summary"
        }
    }

    result = reason(
        {
            "audit_id": "t-002",
            "entity_name": "Test Entity",
            "audit_type": "aml_readiness_review",
            "industry": "fintech",
            "jurisdictions": ["US"],
            "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
            "query_terms": ["aml", "controls"],
            "top_k": 8,
        },
        reasoner=StubReasoner(output=model_output),
        runtime_config={
            "enable_model_reasoning": True,
            "model_overlay_sections": [
                "executive_summary",
                "findings",
                "key_risks",
                "remediation_roadmap",
                "reporting_outputs"
            ],
            "fallback_to_deterministic_on_model_error": True,
            "require_retrieved_chunks_for_model_reasoning": False
        },
    )
    assert result["audit_meta"]["reasoning_mode"] == "hybrid_model_overlay"
    assert result["audit_meta"]["model_version"] == "gpt-5"
    assert result["executive_summary"]["decision_summary"] == "Model-generated summary"
    assert result["reporting_outputs"]["board_ready_summary"] == "Model board summary"
    assert "deployment_decision" in result
    assert "control_assessment" in result
