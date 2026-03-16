from backend.app.schemas.document_compliance import (
    DocumentComplianceOutput,
    TriggeredObligation,
)


def run_document_compliance(document_name: str) -> DocumentComplianceOutput:
    return DocumentComplianceOutput(
        task="document_compliance_analysis",
        document_name=document_name,
        risk_score=76,
        triggered_obligations=[
            TriggeredObligation(
                obligation="Maintain compliance documentation",
                status="PARTIAL",
                basis="Mock global compliance basis",
            )
        ],
        identified_gaps=["Missing full policy coverage"],
        findings=["Document review found partial compliance coverage"],
        confidence=0.94,
    )
