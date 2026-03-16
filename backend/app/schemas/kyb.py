from typing import List, Literal
from pydantic import BaseModel


class KYBInput(BaseModel):
    company_name: str
    jurisdiction: str
    industry: str


class RiskFactor(BaseModel):
    factor: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    reason: str


class KYBOutput(BaseModel):
    task: Literal["kyb_screening"]
    company_name: str
    risk_score: int
    risk_band: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    decision: Literal["PASS", "REVIEW", "FAIL"]
    risk_factors: List[RiskFactor]
    findings: List[str]
    confidence: float
