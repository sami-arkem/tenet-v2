from typing import List
from pydantic import BaseModel


class ControlGap(BaseModel):
    control: str
    severity: str
    reason: str


class GapDetectionInput(BaseModel):
    system_name: str
    jurisdiction: str
    system_type: str
    controls_present: List[str]


class GapDetectionOutput(BaseModel):
    task: str
    system_name: str
    overall_gap_score: int
    missing_controls: List[str]
    control_gaps: List[ControlGap]
    findings: List[str]
    confidence: float
