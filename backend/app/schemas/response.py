"""
Tenet standard API response envelope.
Bible §4.2: every endpoint returns this structure.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    tenet_run_id: Optional[str] = None


class Error(BaseModel):
    code: str               # Machine-readable: "TENANT_NOT_FOUND"
    message: str            # Human-readable
    details: Optional[dict] = None


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: Meta = Field(default_factory=Meta)
    error: Optional[Error] = None

    @classmethod
    def success(
        cls,
        data: T,
        request_id: str | None = None,
        run_id: str | None = None,
    ) -> "ApiResponse[T]":
        meta = Meta(tenet_run_id=run_id)
        if request_id:
            meta.request_id = request_id
        return cls(data=data, meta=meta, error=None)

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        request_id: str | None = None,
        details: dict | None = None,
    ) -> "ApiResponse[None]":
        meta = Meta()
        if request_id:
            meta.request_id = request_id
        return cls(
            data=None,
            meta=meta,
            error=Error(code=code, message=message, details=details),
        )


# Complete error code registry — every error the API can return
ERROR_CODES: dict[str, str] = {
    # Auth
    "UNAUTHORIZED":                "No valid authentication credentials",
    "TOKEN_EXPIRED":               "Authentication token has expired",
    "TOKEN_INVALID":               "Authentication token is invalid",
    "MFA_REQUIRED":                "Multi-factor authentication required",
    "MFA_INVALID":                 "MFA code is incorrect or expired",
    "ACCOUNT_LOCKED":              "Account temporarily locked",
    "INSUFFICIENT_PERMISSIONS":    "Your role does not permit this action",
    # Tenant
    "TENANT_NOT_FOUND":            "Tenant not found",
    "TENANT_SUSPENDED":            "Account suspended",
    "PLAN_LIMIT_EXCEEDED":         "Plan limit reached for this feature",
    # Audit
    "AUDIT_NOT_FOUND":             "Audit run not found",
    "AUDIT_IN_PROGRESS":           "An audit is already running",
    "AUDIT_EVIDENCE_INCOMPLETE":   "Required evidence is missing",
    "AUDIT_INVALID_REGIME":        "Regime not available for this jurisdiction",
    # Evidence
    "EVIDENCE_NOT_FOUND":          "Evidence item not found",
    "EVIDENCE_FILE_TOO_LARGE":     "File exceeds 50MB limit",
    "EVIDENCE_FILE_TYPE_INVALID":  "File type not supported",
    "EVIDENCE_FILE_CORRUPTED":     "File appears to be corrupted",
    "EVIDENCE_DUPLICATE":          "This file has already been uploaded",
    "EVIDENCE_MALWARE_DETECTED":   "File failed security scan",
    "EVIDENCE_PASSWORD_PROTECTED": "File is password-protected",
    # Finding
    "FINDING_NOT_FOUND":           "Finding not found",
    "FINDING_INVALID_STATUS":      "Invalid status transition",
    "FINDING_NOTE_REQUIRED":       "A note is required for this status change",
    # Remediation
    "REMEDIATION_NOT_FOUND":       "Remediation item not found",
    # Filing
    "FILING_NOT_FOUND":            "Filing not found",
    "FILING_INCOMPLETE":           "Required fields are missing",
    "FILING_ALREADY_SUBMITTED":    "This filing has already been submitted",
    "FILING_APPROVAL_REQUIRED":    "Filing must be approved before submission",
    # Validation
    "VALIDATION_ERROR":            "Request data validation failed",
    "REQUIRED_FIELD_MISSING":      "Required field is missing",
    # Rate limiting / infra
    "RATE_LIMIT_EXCEEDED":         "Too many requests. Please slow down.",
    "SERVICE_UNAVAILABLE":         "Service temporarily unavailable",
    "INTERNAL_ERROR":              "An internal error occurred",
}
