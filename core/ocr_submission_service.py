from __future__ import annotations

from pathlib import Path
from typing import Dict

from core.evidence_application_service import EvidenceApplicationPaths, get_evidence_detail
from core.model_call_logger import ModelLogPaths, log_model_call


class OCRSubmissionPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base

    def ocr_text_path(self, audit_id: str, evidence_id: str) -> Path:
        return Path(self.base) / "evidence" / audit_id / "ocr_text" / f"{evidence_id}.txt"


def submit_ocr_text(
    *,
    paths: OCRSubmissionPaths,
    evidence_paths: EvidenceApplicationPaths,
    model_log_paths: ModelLogPaths,
    tenant_id: str,
    evidence_id: str,
    ocr_text: str,
) -> Dict[str, object]:
    detail = get_evidence_detail(
        paths=evidence_paths,
        tenant_id=tenant_id,
        evidence_id=evidence_id,
    )
    if not ocr_text.strip():
        raise ValueError("OCR text cannot be empty")

    output_path = paths.ocr_text_path(detail.audit_id, evidence_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ocr_text, encoding="utf-8")

    log_model_call(
        paths=model_log_paths,
        tenant_id=tenant_id,
        audit_id=detail.audit_id,
        evidence_id=evidence_id,
        surface="evidence_processing",
        model_name="ocr_submission",
        action="manual_ocr_submission",
        status="success",
        input_ref=evidence_id,
        output_ref=str(output_path),
        metadata={"source": "operator"},
    )

    return {
        "evidence_id": evidence_id,
        "audit_id": detail.audit_id,
        "tenant_id": tenant_id,
        "stored_path": str(output_path),
        "message": "OCR text submitted",
    }
