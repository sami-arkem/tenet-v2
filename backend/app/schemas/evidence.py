from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class EvidenceItemResponse(BaseModel):
    id: str
    tenant_id: str
    entity_id: Optional[str] = None
    audit_run_id: Optional[str] = None
    filename: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    file_hash: str
    status: str
    category: Optional[str] = None
    category_confidence: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    is_password_protected: bool
    processing_error: Optional[str] = None
    supersedes_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EvidenceListResponse(BaseModel):
    items: list[EvidenceItemResponse]
    total: int


class CreateUploadSessionRequest(BaseModel):
    entity_id: Optional[UUID] = None
    audit_run_id: Optional[str] = None
    filename: str
    mime_type: str
    file_size_bytes: int


class UploadSessionResponse(BaseModel):
    id: str
    status: str
    upload_url: Optional[str] = None    # presigned URL for direct upload
    storage_path: Optional[str] = None
    expires_at: datetime
