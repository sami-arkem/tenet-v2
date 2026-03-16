from backend.app.schemas.risk_classification import RiskClassificationOutput


def run_risk_classification(system_name: str) -> RiskClassificationOutput:
    return RiskClassificationOutput(
        task="risk_classification",
        system_name=system_name,
        overall_risk_score=85,
        risk_tier="HIGH_RISK",
        triggered_categories=["credit_decisioning"],
        applicable_regulations=["EU AI Act Annex III"],
        required_controls=["human_oversight", "bias_testing", "explainability"],
        findings=["Mock high-risk classification result"],
        confidence=0.94,
    )
