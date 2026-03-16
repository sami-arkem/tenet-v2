from typing import List, Literal
from pydantic import BaseModel


class KYCInput(BaseModel):
    full_name: str
    entity_type: Literal["individual"]


class MatchedSource(BaseModel):
    source: str
    matched_name: str
    confidence: float
    reason: str


class KYCOutput(BaseModel):
    task: Literal["kyc_screening"]
    entity_name: str
    risk_score: int
    risk_band: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    decision: Literal["PASS", "REVIEW", "FAIL"]
    findings: List[str]
    confidence: float
