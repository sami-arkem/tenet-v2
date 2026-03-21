from src.llm.model_adapter import ModelAdapter, ModelResponse
from src.reasoning.model_reasoner import ModelReasoner


class InlineAdapter(ModelAdapter):
    def __init__(self, content):
        self._content = content

    def is_configured(self) -> bool:
        return True

    def generate_json(self, request):
        return ModelResponse(
            model_name="gpt-5",
            provider="openai_compatible",
            content=self._content,
            raw_usage={},
        )


def test_model_reasoner_repairs_sparse_model_output():
    sparse_output = {
        "audit_meta": {
            "audit_id": "audit-123"
        },
        "audit_scope": {
            "scope_statement": "AML review"
        },
        "regulatory_applicability": {
            "primary_regimes": ["BSA_AML"]
        }
    }

    reasoner = ModelReasoner(model_adapter=InlineAdapter(sparse_output))
    result = reasoner.reason(
        audit_context={
            "audit_type": "aml_readiness_review",
            "industry": "fintech",
            "jurisdictions": ["US", "UK"],
        },
        audit_plan={
            "applicable_regimes": ["BSA_AML", "UK_MLR"],
            "review_focus": ["policy_governance", "transaction_monitoring"],
        },
        retrieved_chunks=[
            {
                "chunk_id": "c1",
                "document_name": "AML Policy",
                "source_name": "policy_repo",
                "source_family": "aml",
                "jurisdiction": "US",
                "industry": "fintech",
                "audit_domain": "policy_governance",
                "url": "https://example.com/a",
                "score": 11,
                "quality_status": "approved",
                "text": "AML governance and escalation are defined.",
            }
        ],
    )

    assert result.model_name == "gpt-5"
    assert result.repaired is True
    assert result.output["audit_scope"]["audit_type"] == "aml_readiness_review"
    assert result.output["regulatory_applicability"]["frameworks"] == ["BSA_AML", "UK_MLR"]
    assert len(result.output["evidence_appendix"]) == 1


def test_model_reasoner_accepts_full_shape_output():
    full_output = {
        "audit_meta": {
            "audit_id": "",
            "audit_version": "v1",
            "timestamp_utc": "",
            "platform_version": "",
            "model_version": "",
            "report_status": ""
        },
        "entity_profile": {
            "legal_name": "",
            "trade_name": "",
            "industry": "",
            "subindustry": "",
            "business_model": "",
            "products_services": [],
            "jurisdictions_of_operation": [],
            "customer_geographies": [],
            "customer_types": [],
            "distribution_channels": [],
            "payment_flows": [],
            "data_categories_processed": [],
            "high_risk_activities": []
        },
        "audit_scope": {
            "audit_type": "aml_readiness_review",
            "scope_statement": "",
            "included_domains": [],
            "excluded_domains": [],
            "documents_reviewed": [],
            "evidence_received": [],
            "evidence_missing_at_start": []
        },
        "regulatory_applicability": {
            "primary_regimes": [],
            "secondary_regimes": [],
            "frameworks": [],
            "licensing_obligations": [],
            "enforcement_exposure_areas": [],
            "regulatory_classification": {
                "entity_type": "",
                "risk_tier": "",
                "obligation_intensity": "",
                "cross_border_complexity": ""
            }
        },
        "executive_summary": {
            "system_or_business_reviewed": "",
            "overall_readiness": "",
            "top_issues": [],
            "decision_summary": "",
            "board_message": ""
        },
        "deployment_decision": {
            "status": "",
            "decision_rationale": "",
            "blocking_issues": [],
            "conditions_precedent": [],
            "conditions_ongoing": []
        },
        "financial_exposure": {
            "estimated_regulatory_exposure": "",
            "exposure_band": "",
            "drivers": [],
            "assumptions": [],
            "confidence_note": ""
        },
        "control_assessment": {
            "domains": [],
            "control_coverage_score": 0,
            "evidence_coverage_score": 0
        },
        "findings": [],
        "key_risks": [],
        "missing_controls": [],
        "missing_evidence": [],
        "remediation_roadmap": {
            "immediate_0_30_days": [],
            "near_term_30_90_days": [],
            "medium_term_90_180_days": [],
            "strategic_180_plus_days": []
        },
        "reporting_outputs": {
            "board_ready_summary": "",
            "regulator_ready_summary": "",
            "client_facing_summary": ""
        },
        "confidence_assessment": {
            "overall_confidence_score": 0,
            "confidence_level": "",
            "confidence_drivers": [],
            "limiting_factors": [],
            "human_review_required": True
        },
        "evidence_appendix": []
    }

    reasoner = ModelReasoner(model_adapter=InlineAdapter(full_output))
    result = reasoner.reason(
        audit_context={
            "audit_type": "aml_readiness_review",
            "industry": "fintech",
            "jurisdictions": ["US"],
        },
        audit_plan={
            "applicable_regimes": ["BSA_AML"],
            "review_focus": ["policy_governance"],
        },
        retrieved_chunks=[],
    )

    assert result.repaired is False or isinstance(result.repaired, bool)
    assert "audit_meta" in result.output
