from typing import List, Literal
from pydantic import BaseModel


class RiskClassificationInput(BaseModel):
    system_name: str
    system_description: str
    jurisdiction: str
    use_case: str
    sector: str


class RiskClassificationOutput(BaseModel):
    task: Literal["risk_classification"]
    system_name: str
    overall_risk_score: int
    risk_tier: Literal["MINIMAL", "LIMITED", "HIGH_RISK", "PROHIBITED"]
    triggered_categories: List[str]
    applicable_regulations: List[str]
    required_controls: List[str]
    findings: List[str]
    confidence: float
