from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel

ChecklistStatus = Literal[
    "MISSING",
    "UPLOADING",
    "PROCESSING",
    "READY",
    "OCR_REQUIRED",
    "REVIEW_REQUIRED",
    "FAILED",
]

PreparationStatus = Literal["BLOCKED", "READY"]


class EvidenceChecklistItem(BaseModel):
    requirement_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    framework: str
    required_category: str
    label: str
    status: ChecklistStatus
    linked_evidence_ids: List[str]
    blocking_reasons: List[str]
    predicted_categories: List[str]
    final_categories: List[str]


class AuditPreparationSummary(BaseModel):
    audit_id: str
    tenant_id: str
    preparation_status: PreparationStatus
    total_requirements: int
    total_ready: int
    total_blocked: int
    checklist: List[EvidenceChecklistItem]
    blocking_reasons: List[str]


class OCRSubmissionRequest(BaseModel):
    ocr_text: str


class OCRSubmissionResponse(BaseModel):
    evidence_id: str
    audit_id: str
    tenant_id: str
    stored_path: str
    message: str


class ModelCallLogRow(BaseModel):
    call_id: str
    tenant_id: str
    audit_id: str
    evidence_id: Optional[str] = None
    surface: str
    model_name: str
    action: str
    status: str
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    metadata: dict
    created_at: str
