from backend.app.schemas.kyb import KYBOutput, RiskFactor


def run_kyb_screening(company_name: str) -> KYBOutput:
    return KYBOutput(
        task="kyb_screening",
        company_name=company_name,
        risk_score=72,
        risk_band="HIGH",
        decision="REVIEW",
        risk_factors=[
            RiskFactor(
                factor="jurisdiction_risk",
                severity="HIGH",
                reason="Mock elevated jurisdiction risk",
            )
        ],
        findings=["Mock KYB screening result"],
        confidence=0.93,
    )
