from backend.app.schemas.kyc import KYCOutput


def run_kyc_screening(full_name: str) -> KYCOutput:
    return KYCOutput(
        task="kyc_screening",
        entity_name=full_name,
        risk_score=10,
        risk_band="LOW",
        decision="PASS",
        findings=["Mock screening result"],
        confidence=0.95,
    )
