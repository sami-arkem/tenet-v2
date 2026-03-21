from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

EvidenceStatus = Literal["UPLOADING", "PROCESSING", "READY", "FAILED", "CANCELLED"]


class RegisterEvidenceUploadRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    sha256: str = Field(min_length=32)
    byte_size: int = Field(gt=0)
    evidence_category: str = Field(min_length=1)
    note: Optional[str] = None
    supersedes_id: Optional[str] = None


class CompleteEvidenceUploadRequest(BaseModel):
    storage_path: str = Field(min_length=1)
    processing_started: bool = True


class FailEvidenceUploadRequest(BaseModel):
    error_message: str = Field(min_length=3)


class CancelEvidenceUploadRequest(BaseModel):
    note: Optional[str] = None


class MarkEvidenceReadyRequest(BaseModel):
    extracted_text_ready: bool = True
    inventory_ready: bool = True


class EvidenceSummary(BaseModel):
    evidence_id: str
    audit_id: str
    tenant_id: str
    filename: str
    content_type: str
    sha256: str
    byte_size: int
    evidence_category: str
    status: EvidenceStatus
    supersedes_id: Optional[str] = None
    version_number: int
    created_at: str
    updated_at: str


class EvidenceDetail(EvidenceSummary):
    storage_path: Optional[str] = None
    processing_error: Optional[str] = None
    extracted_text_ready: bool
    inventory_ready: bool
    immutable_after_ready: bool
    note: Optional[str] = None


class EvidenceListResponse(BaseModel):
    audit_id: Optional[str] = None
    total_items: int
    total_ready: int
    total_processing: int
    total_failed: int
    total_cancelled: int
    rows: List[EvidenceSummary]


class AuditEvidenceGateResponse(BaseModel):
    audit_id: str
    gate_name: str
    gate_status: str
    evidence_ready: bool
    waiting_file_count: int
    total_files: int
    total_ready_files: int
    blocking_reasons: List[str]
    required_categories: List[str]
    ready_categories: List[str]
