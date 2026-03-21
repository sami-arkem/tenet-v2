from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.evidence_pack_service import DEFAULT_PACK_ROOT, EvidencePackPaths, get_evidence_pack


DEFAULT_EVIDENCE_ROOT = Path("artifacts") / "evidence_blobs"

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".json",
    ".csv",
}

EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".csv": "text/csv",
}


class EvidenceIngestionError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIngestionError(f"{field_name} must be a non-empty string")
    return value.strip()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower().strip()
    if not ext:
        raise EvidenceIngestionError("filename must include an extension")
    if ext not in ALLOWED_EXTENSIONS:
        raise EvidenceIngestionError(f"unsupported file extension: {ext}")
    return ext


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sniff_mime(data: bytes, ext: str) -> str:
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise EvidenceIngestionError("invalid pdf signature")
        return "application/pdf"

    if ext in {".txt", ".md"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceIngestionError("text file must be valid utf-8") from exc
        return EXTENSION_TO_MIME[ext]

    if ext == ".json":
        try:
            json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise EvidenceIngestionError("invalid json file") from exc
        return "application/json"

    if ext == ".csv":
        try:
            text = data.decode("utf-8")
            reader = csv.reader(io.StringIO(text))
            next(reader, None)
        except Exception as exc:
            raise EvidenceIngestionError("invalid csv file") from exc
        return "text/csv"

    raise EvidenceIngestionError(f"unsupported extension for sniffing: {ext}")


def _detect_password_protected_pdf(data: bytes) -> bool:
    if not data.startswith(b"%PDF-"):
        return False
    return b"/Encrypt" in data[:8192]


def _read_or_seed_evidence_index(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    paths = EvidencePackPaths.for_pack(pack_id, pack_root)
    index_path = paths.root / "evidence_index.json"
    if index_path.exists():
        payload = _load_json(index_path)
        if not isinstance(payload, dict):
            raise EvidenceIngestionError("evidence_index.json must be an object")
        return payload

    payload = {
        "pack_id": pack_id,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "items": [],
    }
    _atomic_write_json(index_path, payload)
    return payload


def _update_pack_manifest_evidence_catalog(
    *,
    pack_id: str,
    evidence_row: dict[str, Any],
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> None:
    paths = EvidencePackPaths.for_pack(pack_id, pack_root)
    manifest = _load_json(paths.manifest_path)
    evidence_catalog = manifest.get("evidence_catalog")
    if not isinstance(evidence_catalog, list):
        raise EvidenceIngestionError("manifest.evidence_catalog must be a list")

    evidence_id = evidence_row["evidence_id"]
    if any(isinstance(row, dict) and row.get("evidence_id") == evidence_id for row in evidence_catalog):
        return

    evidence_catalog.append(
        {
            "evidence_id": evidence_row["evidence_id"],
            "title": evidence_row["title"],
            "source_type": evidence_row["source_type"],
            "file_path": evidence_row["storage_path"],
            "citation": evidence_row["citation"],
        }
    )
    _atomic_write_json(paths.manifest_path, manifest)

    detail = _load_json(paths.detail_path)
    if isinstance(detail, dict):
        manifest_summary = detail.get("manifest_summary")
        if isinstance(manifest_summary, dict):
            manifest_summary["evidence_count"] = len(evidence_catalog)
            detail["updated_at"] = utc_now_iso()
            _atomic_write_json(paths.detail_path, detail)


def ingest_evidence_file(
    *,
    pack_id: str,
    filename: str,
    data: bytes,
    title: str,
    source_type: str,
    citation: str,
    strict_pdf_encryption_block: bool = True,
    pack_root: Path = DEFAULT_PACK_ROOT,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
) -> dict[str, Any]:
    pack_id = _require_non_empty_str(pack_id, "pack_id")
    filename = _require_non_empty_str(filename, "filename")
    title = _require_non_empty_str(title, "title")
    source_type = _require_non_empty_str(source_type, "source_type")
    citation = _require_non_empty_str(citation, "citation")

    get_evidence_pack(pack_id, pack_root=pack_root)

    if not isinstance(data, (bytes, bytearray)) or not data:
        raise EvidenceIngestionError("data must be non-empty bytes")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise EvidenceIngestionError(f"file exceeds max size of {MAX_FILE_SIZE_BYTES} bytes")

    ext = _normalize_ext(filename)
    detected_mime = _sniff_mime(bytes(data), ext)

    if ext == ".pdf" and strict_pdf_encryption_block and _detect_password_protected_pdf(bytes(data)):
        raise EvidenceIngestionError("password-protected or encrypted pdf is not allowed for deterministic ingestion")

    sha256 = _sha256_bytes(bytes(data))
    evidence_id = f"evidence_{sha256[:16]}"
    storage_dir = evidence_root / pack_id
    storage_filename = f"{sha256}{ext}"
    storage_path = storage_dir / storage_filename

    if not storage_path.exists():
        _atomic_write_bytes(storage_path, bytes(data))

    evidence_row = {
        "evidence_id": evidence_id,
        "filename": filename,
        "title": title,
        "source_type": source_type,
        "detected_mime": detected_mime,
        "size_bytes": len(data),
        "sha256": sha256,
        "storage_path": str(storage_path),
        "citation": citation,
        "processing_status": "UPLOADED",
        "malware_scan_status": "NOT_RUN",
        "ocr_status": "NOT_REQUIRED" if ext != ".pdf" else "PENDING",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }

    index = _read_or_seed_evidence_index(pack_id, pack_root=pack_root)
    items = index.get("items")
    if not isinstance(items, list):
        raise EvidenceIngestionError("evidence_index.items must be a list")

    existing = None
    for row in items:
        if isinstance(row, dict) and row.get("evidence_id") == evidence_id:
            existing = row
            break

    if existing is None:
        items.append(evidence_row)
        index["updated_at"] = utc_now_iso()
        index_path = EvidencePackPaths.for_pack(pack_id, pack_root).root / "evidence_index.json"
        _atomic_write_json(index_path, index)
        _update_pack_manifest_evidence_catalog(pack_id=pack_id, evidence_row=evidence_row, pack_root=pack_root)
        return evidence_row

    return existing


def list_evidence_items(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> list[dict[str, Any]]:
    get_evidence_pack(pack_id, pack_root=pack_root)
    index = _read_or_seed_evidence_index(pack_id, pack_root=pack_root)
    items = index.get("items")
    if not isinstance(items, list):
        raise EvidenceIngestionError("evidence_index.items must be a list")
    return items
