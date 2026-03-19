from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Protocol

from core.evidence_ingestion_service import list_evidence_items
from core.evidence_pack_service import DEFAULT_PACK_ROOT, EvidencePackPaths, get_evidence_pack


VALID_PROCESSING_STATUS = {
    "UPLOADED",
    "SCANNING",
    "SCAN_FAILED",
    "EXTRACTING",
    "EXTRACTION_FAILED",
    "CLASSIFYING",
    "CLASSIFICATION_FAILED",
    "EXTRACTING_FACTS",
    "READY",
    "FAILED",
}
HIGH_CONFIDENCE = {"HIGH"}


class EvidenceProcessingError(RuntimeError):
    pass


class Classifier(Protocol):
    def classify(self, *, filename: str, text: str) -> dict[str, Any]:
        """
        Returns:
        {
          "category": str,
          "confidence": "HIGH" | "MEDIUM" | "LOW" | "MANUAL" | "UNCLASSIFIED",
          "reason": str
        }
        """


class FactExtractor(Protocol):
    def extract(self, *, category: str, text: str) -> dict[str, Any]:
        """
        Returns schema-constrained facts for the given category.
        """


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceProcessingError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pack_index_path(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "evidence_index.json"


def _processing_root(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "processing"


def _load_index(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    path = _pack_index_path(pack_id, pack_root)
    if not path.exists():
        raise FileNotFoundError(f"evidence index not found for pack: {pack_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise EvidenceProcessingError("evidence_index.json must be an object")
    items = payload.get("items")
    if not isinstance(items, list):
        raise EvidenceProcessingError("evidence_index.items must be a list")
    return payload


def _write_index(pack_id: str, payload: dict[str, Any], pack_root: Path = DEFAULT_PACK_ROOT) -> None:
    _atomic_write_json(_pack_index_path(pack_id, pack_root), payload)


def _find_item(index: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    for row in index["items"]:
        if isinstance(row, dict) and row.get("evidence_id") == evidence_id:
            return row
    raise FileNotFoundError(f"evidence item not found: {evidence_id}")


def _set_status(
    *,
    row: dict[str, Any],
    status: str,
    error_detail: str | None = None,
) -> None:
    if status not in VALID_PROCESSING_STATUS:
        raise EvidenceProcessingError(f"invalid processing status: {status}")
    row["processing_status"] = status
    if error_detail is None:
        row.pop("error_detail", None)
    else:
        row["error_detail"] = error_detail


def _read_bytes(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"blob not found: {path}")
    return path.read_bytes()


def _extract_pdf_text(data: bytes) -> str:
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:
        raise EvidenceProcessingError("pdf extraction requires pdfplumber to be installed") from exc

    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = Path(tmp.name)
        try:
            texts: list[str] = []
            with pdfplumber.open(str(tmp_path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        texts.append(page_text)
            extracted = "\n\n".join(texts).strip()
            if not extracted:
                raise EvidenceProcessingError("pdf text extraction produced empty text")
            return extracted
        finally:
            tmp_path.unlink(missing_ok=True)
    except EvidenceProcessingError:
        raise
    except Exception as exc:
        raise EvidenceProcessingError(f"pdf extraction failed: {exc}") from exc


def _extract_text_for_item(row: dict[str, Any]) -> str:
    storage_path = Path(_require_non_empty_str(row.get("storage_path"), "storage_path"))
    detected_mime = _require_non_empty_str(row.get("detected_mime"), "detected_mime")
    data = _read_bytes(storage_path)

    if detected_mime in {"text/plain", "text/markdown"}:
        return data.decode("utf-8").strip()
    if detected_mime == "application/json":
        payload = json.loads(data.decode("utf-8"))
        return json.dumps(payload, indent=2, sort_keys=True)
    if detected_mime == "text/csv":
        text = data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise EvidenceProcessingError("csv is empty")
        preview = rows[:20]
        return "\n".join([", ".join(map(str, row)) for row in preview]).strip()
    if detected_mime == "application/pdf":
        return _extract_pdf_text(data)
    raise EvidenceProcessingError(f"unsupported mime for extraction: {detected_mime}")


class RuleBasedClassifier:
    """
    Deterministic fallback for local/dev/test.
    Production can swap this with a model-backed adapter without changing pipeline code.
    """

    def classify(self, *, filename: str, text: str) -> dict[str, Any]:
        lowered = f"{filename}\n{text[:3000]}".lower()

        rules = [
            ("screening_alert_log", ["sanctions", "screening", "ofac", "watchlist"]),
            ("monitoring_report", ["transaction monitoring", "monitoring report", "alert escalation"]),
            ("policy_document", ["policy", "procedure", "governance", "standard"]),
            ("owner_matrix", ["owner matrix", "ownership", "raci"]),
            ("vendor_due_diligence", ["vendor due diligence", "third party", "supplier review"]),
            ("periodic_review_log", ["periodic review", "cdd review", "kyc refresh"]),
        ]

        for category, needles in rules:
            if any(needle in lowered for needle in needles):
                return {
                    "category": category,
                    "confidence": "HIGH",
                    "reason": f"matched deterministic rule for {category}",
                }

        return {
            "category": "unclassified",
            "confidence": "UNCLASSIFIED",
            "reason": "no deterministic classification rule matched",
        }


class RuleBasedFactExtractor:
    """
    Deterministic baseline extractor.
    Keeps pipeline executable and testable.
    """

    def extract(self, *, category: str, text: str) -> dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return {
            "category": category,
            "line_count": len(lines),
            "char_count": len(text),
            "preview": "\n".join(lines[:5])[:1000],
        }


def process_evidence_item(
    *,
    pack_id: str,
    evidence_id: str,
    classifier: Classifier | None = None,
    fact_extractor: FactExtractor | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    get_evidence_pack(pack_id, pack_root=pack_root)

    classifier = classifier or RuleBasedClassifier()
    fact_extractor = fact_extractor or RuleBasedFactExtractor()

    index = _load_index(pack_id, pack_root)
    row = _find_item(index, evidence_id)
    processing_root = _processing_root(pack_id, pack_root)
    processing_root.mkdir(parents=True, exist_ok=True)

    extracted_text_path = processing_root / f"{evidence_id}.txt"
    classification_path = processing_root / f"{evidence_id}.classification.json"
    facts_path = processing_root / f"{evidence_id}.facts.json"

    try:
        _set_status(row=row, status="EXTRACTING")
        _write_index(pack_id, index, pack_root)

        extracted_text = _extract_text_for_item(row)
        if not extracted_text.strip():
            raise EvidenceProcessingError("extracted text is empty")

        _atomic_write_text(extracted_text_path, extracted_text.rstrip() + "\n")

        _set_status(row=row, status="CLASSIFYING")
        row["extracted_text_path"] = str(extracted_text_path)
        _write_index(pack_id, index, pack_root)

        classification = classifier.classify(
            filename=_require_non_empty_str(row.get("filename"), "filename"),
            text=extracted_text[:3000],
        )
        if not isinstance(classification, dict):
            raise EvidenceProcessingError("classifier must return an object")

        category = _require_non_empty_str(classification.get("category"), "classification.category")
        confidence = _require_non_empty_str(classification.get("confidence"), "classification.confidence")
        reason = _require_non_empty_str(classification.get("reason"), "classification.reason")

        classification_payload = {
            "evidence_id": evidence_id,
            "category": category,
            "confidence": confidence,
            "reason": reason,
        }
        _atomic_write_json(classification_path, classification_payload)

        row["classification"] = classification_payload
        row["classification_path"] = str(classification_path)

        if confidence in HIGH_CONFIDENCE:
            _set_status(row=row, status="EXTRACTING_FACTS")
            _write_index(pack_id, index, pack_root)

            facts = fact_extractor.extract(category=category, text=extracted_text)
            if not isinstance(facts, dict):
                raise EvidenceProcessingError("fact_extractor must return an object")

            _atomic_write_json(facts_path, facts)
            row["key_facts"] = facts
            row["key_facts_path"] = str(facts_path)

        _set_status(row=row, status="READY")
        _write_index(pack_id, index, pack_root)
        return row

    except Exception as exc:
        failure_status = "FAILED"
        message = str(exc)
        if row.get("processing_status") == "EXTRACTING":
            failure_status = "EXTRACTION_FAILED"
        elif row.get("processing_status") == "CLASSIFYING":
            failure_status = "CLASSIFICATION_FAILED"

        _set_status(row=row, status=failure_status, error_detail=message)
        _write_index(pack_id, index, pack_root)
        raise


def build_corpus_readiness(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    get_evidence_pack(pack_id, pack_root=pack_root)
    try:
        items = list_evidence_items(pack_id, pack_root=pack_root)
    except FileNotFoundError:
        items = []

    ready = 0
    failed = 0
    pending = 0
    statuses: dict[str, int] = {}
    failures: list[dict[str, Any]] = []

    for row in items:
        if not isinstance(row, dict):
            continue
        status = str(row.get("processing_status", "UNKNOWN"))
        statuses[status] = statuses.get(status, 0) + 1

        if status == "READY":
            ready += 1
        elif status in {"SCAN_FAILED", "EXTRACTION_FAILED", "CLASSIFICATION_FAILED", "FAILED"}:
            failed += 1
            failures.append(
                {
                    "evidence_id": row.get("evidence_id"),
                    "filename": row.get("filename"),
                    "status": status,
                    "error_detail": row.get("error_detail"),
                }
            )
        else:
            pending += 1

    corpus_ready = len(items) > 0 and failed == 0 and pending == 0
    return {
        "pack_id": pack_id,
        "item_count": len(items),
        "ready_count": ready,
        "failed_count": failed,
        "pending_count": pending,
        "corpus_ready": corpus_ready,
        "statuses": dict(sorted(statuses.items())),
        "failures": failures,
        "event": "CORPUS_READY" if corpus_ready else None,
    }


def process_all_evidence_for_pack(
    *,
    pack_id: str,
    classifier: Classifier | None = None,
    fact_extractor: FactExtractor | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    items = list_evidence_items(pack_id, pack_root=pack_root)
    processed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for row in items:
        evidence_id = _require_non_empty_str(row.get("evidence_id"), "evidence_id")
        try:
            processed.append(
                process_evidence_item(
                    pack_id=pack_id,
                    evidence_id=evidence_id,
                    classifier=classifier,
                    fact_extractor=fact_extractor,
                    pack_root=pack_root,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "evidence_id": evidence_id,
                    "filename": row.get("filename"),
                    "error": str(exc),
                }
            )

    readiness = build_corpus_readiness(pack_id, pack_root=pack_root)
    return {
        "pack_id": pack_id,
        "processed_count": len(processed),
        "failure_count": len(failures),
        "failures": failures,
        "readiness": readiness,
    }
