from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

EvidenceJobStatus = Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]


class EvidenceJobSummary(BaseModel):
    job_id: str
    evidence_id: str
    audit_id: Optional[str]
    tenant_id: str
    status: EvidenceJobStatus
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class EvidenceJobListResponse(BaseModel):
    total_items: int
    total_queued: int
    total_processing: int
    total_completed: int
    total_failed: int
    rows: List[EvidenceJobSummary]
