from typing import List
from pydantic import BaseModel


class TriggeredObligation(BaseModel):
    obligation: str
    status: str
    basis: str


class DocumentComplianceInput(BaseModel):
    document_name: str
    document_type: str
    document_text: str
    jurisdiction: str


class DocumentComplianceOutput(BaseModel):
    task: str
    document_name: str
    risk_score: int
    triggered_obligations: List[TriggeredObligation]
    identified_gaps: List[str]
    findings: List[str]
    confidence: float
