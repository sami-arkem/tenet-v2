from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class EvidenceClassificationPaths:
    def __init__(self, base: str = "state") -> None:
        self.base = base
        self.classifications = f"{base}/evidence/evidence_classifications.jsonl"


def _load_rows(paths: EvidenceClassificationPaths) -> List[Dict[str, object]]:
    rows = _read_jsonl(Path(paths.classifications))
    rows.sort(key=lambda row: (row["tenant_id"], row["audit_id"], row["evidence_id"]))
    return rows


def _write_rows(paths: EvidenceClassificationPaths, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["audit_id"], row["evidence_id"]))
    _write_jsonl(Path(paths.classifications), rows)


def upsert_classification_record(
    *,
    paths: EvidenceClassificationPaths,
    evidence_id: str,
    audit_id: str,
    tenant_id: str,
    extracted_text_path: Optional[str],
    predicted_category: Optional[str],
    final_category: Optional[str],
    confidence: Optional[str],
    confidence_score: float,
    classification_status: Optional[str],
    requires_user_confirmation: bool,
    manually_classified: bool,
    review_queue_status: str,
    ocr_required: bool,
    processing_error_code: Optional[str],
    processing_error_message: Optional[str],
) -> Dict[str, object]:
    rows = _load_rows(paths)
    now = _now_iso()
    existing = None
    for row in rows:
        if str(row["evidence_id"]) == evidence_id and str(row["tenant_id"]) == tenant_id:
            existing = row
            break

    payload = {
        "evidence_id": evidence_id,
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "predicted_category": predicted_category,
        "final_category": final_category,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "classification_status": classification_status,
        "requires_user_confirmation": requires_user_confirmation,
        "manually_classified": manually_classified,
        "review_queue_status": review_queue_status,
        "ocr_required": ocr_required,
        "extracted_text_path": extracted_text_path,
        "processing_error_code": processing_error_code,
        "processing_error_message": processing_error_message,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }

    if existing is None:
        rows.append(payload)
    else:
        rows = [payload if (str(row["evidence_id"]) == evidence_id and str(row["tenant_id"]) == tenant_id) else row for row in rows]

    _write_rows(paths, rows)
    return payload


def list_classifications(
    *,
    paths: EvidenceClassificationPaths,
    tenant_id: str,
    audit_id: Optional[str] = None,
) -> Dict[str, object]:
    rows = [row for row in _load_rows(paths) if str(row["tenant_id"]) == tenant_id]
    if audit_id:
        rows = [row for row in rows if str(row["audit_id"]) == audit_id]

    return {
        "total_items": len(rows),
        "total_pending_review": sum(1 for row in rows if str(row.get("review_queue_status")) == "CLASSIFICATION_REVIEW_REQUIRED"),
        "total_ocr_required": sum(1 for row in rows if bool(row.get("ocr_required", False))),
        "total_retryable_failures": sum(1 for row in rows if str(row.get("review_queue_status")) == "FAILED_RETRYABLE"),
        "rows": rows,
    }


def get_classification(
    *,
    paths: EvidenceClassificationPaths,
    tenant_id: str,
    evidence_id: str,
) -> Dict[str, object]:
    rows = _load_rows(paths)
    for row in rows:
        if str(row["tenant_id"]) == tenant_id and str(row["evidence_id"]) == evidence_id:
            return row
    raise ValueError(f"Classification not found: {evidence_id}")


def apply_manual_override(
    *,
    paths: EvidenceClassificationPaths,
    tenant_id: str,
    evidence_id: str,
    final_category: str,
) -> Dict[str, object]:
    ALL_CLASSIFICATION_CATEGORIES = ["policy", "governance", "risk_assessment", "model_card", "testing", "financials"]
    if final_category not in ALL_CLASSIFICATION_CATEGORIES:
        raise ValueError("Invalid classification category")

    row = get_classification(
        paths=paths,
        tenant_id=tenant_id,
        evidence_id=evidence_id,
    )

    updated = upsert_classification_record(
        paths=paths,
        evidence_id=evidence_id,
        audit_id=str(row["audit_id"]),
        tenant_id=tenant_id,
        extracted_text_path=row.get("extracted_text_path"),
        predicted_category=row.get("predicted_category"),
        final_category=final_category,
        confidence=row.get("confidence"),
        confidence_score=float(row.get("confidence_score", 0.0)),
        classification_status="MANUAL_CONFIRMED",
        requires_user_confirmation=False,
        manually_classified=True,
        review_queue_status="NONE",
        ocr_required=bool(row.get("ocr_required", False)),
        processing_error_code=row.get("processing_error_code"),
        processing_error_message=row.get("processing_error_message"),
    )
    return updated


def classify_document_text(text: str) -> Dict[str, object]:
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "policy": [
            "policy",
            "aml policy",
            "anti money laundering policy",
            "governance policy",
            "human oversight",
            "monitoring policy",
        ],
        "governance": [
            "board",
            "committee",
            "oversight",
            "governance",
            "minutes",
            "escalation",
        ],
        "risk_assessment": [
            "risk assessment",
            "inherent risk",
            "residual risk",
            "control effectiveness",
        ],
        "model_card": [
            "model card",
            "intended use",
            "limitations",
            "model version",
            "training data",
        ],
        "testing": [
            "bias testing",
            "validation",
            "test result",
            "accuracy",
            "false positive",
            "false negative",
        ],
        "financials": [
            "balance sheet",
            "income statement",
            "cash flow",
            "trial balance",
            "general ledger",
        ],
    }

    def _normalize(t: str) -> str:
        return " ".join(t.lower().split())

    normalized = _normalize(text)
    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in normalized:
                score += 1
        scores[category] = score

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]
    total_hits = sum(scores.values())

    if best_score >= 4:
        confidence = "HIGH"
        confidence_score = 0.95
        status = "AUTO_CONFIRMED"
        requires_user_confirmation = False
    elif best_score >= 2:
        confidence = "MEDIUM"
        confidence_score = 0.70
        status = "PENDING_CONFIRMATION"
        requires_user_confirmation = True
    else:
        confidence = "LOW"
        confidence_score = 0.35 if total_hits > 0 else 0.0
        best_category = None
        status = "PENDING_CONFIRMATION"
        requires_user_confirmation = True

    return {
        "predicted_category": best_category,
        "final_category": best_category,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "classification_status": status,
        "requires_user_confirmation": requires_user_confirmation,
        "manually_classified": False,
    }
