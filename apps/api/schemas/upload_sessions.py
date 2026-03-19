from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

UploadSessionStatus = Literal["CREATED", "UPLOADING", "FINALIZING", "COMPLETED", "FAILED", "CANCELLED"]


class CreateUploadSessionRequest(BaseModel):
    audit_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    sha256: str = Field(min_length=32)
    byte_size: int = Field(gt=0)
    evidence_category: str = Field(min_length=1)
    note: Optional[str] = None
    supersedes_id: Optional[str] = None


class FinalizeUploadSessionRequest(BaseModel):
    temp_file_path: str = Field(min_length=1)


class FailUploadSessionRequest(BaseModel):
    error_message: str = Field(min_length=3)


class CancelUploadSessionRequest(BaseModel):
    note: Optional[str] = None


class UploadSessionSummary(BaseModel):
    upload_session_id: str
    audit_id: str
    tenant_id: str
    filename: str
    content_type: str
    sha256: str
    byte_size: int
    evidence_category: str
    status: UploadSessionStatus
    blob_id: Optional[str] = None
    storage_path: Optional[str] = None
    evidence_id: Optional[str] = None
    created_at: str
    updated_at: str


class UploadSessionListResponse(BaseModel):
    total_items: int
    total_created: int
    total_uploading: int
    total_finalizing: int
    total_completed: int
    total_failed: int
    total_cancelled: int
    rows: List[UploadSessionSummary]
