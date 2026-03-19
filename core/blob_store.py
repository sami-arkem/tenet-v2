from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


MAX_FILE_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".json"}
SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _safe_filename(filename: str) -> str:
    keep = []
    for ch in filename:
        if ch.isalnum() or ch in {".", "-", "_"}:
            keep.append(ch)
        else:
            keep.append("_")
    cleaned = "".join(keep).strip("._")
    return cleaned or "file.bin"


@dataclass(frozen=True)
class BlobStorePaths:
    base_dir: str

    @property
    def manifests_dir(self) -> Path:
        return Path(self.base_dir) / "blob_store" / "manifests"

    @property
    def objects_dir(self) -> Path:
        return Path(self.base_dir) / "blob_store" / "objects"


def validate_upload_candidate(
    *,
    temp_file_path: Path,
    expected_content_type: str,
    expected_sha256: str,
    expected_byte_size: int,
) -> None:
    if not temp_file_path.exists():
        raise ValueError("Uploaded file not found")

    actual_size = temp_file_path.stat().st_size
    if actual_size <= 0:
        raise ValueError("This file appears to be empty.")
    if actual_size > MAX_FILE_BYTES:
        raise ValueError("File too large. Maximum 50MB.")
    if actual_size != expected_byte_size:
        raise ValueError("Uploaded file size does not match declared byte size")

    ext = temp_file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("File type not supported")
    if expected_content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError("File type not supported")

    actual_sha = _sha256_file(temp_file_path)
    if actual_sha != expected_sha256:
        raise ValueError("Uploaded file checksum does not match registered SHA-256")

    guessed_type, _ = mimetypes.guess_type(temp_file_path.name)
    if expected_content_type == "application/pdf" and guessed_type not in {None, "application/pdf"}:
        raise ValueError("MIME mismatch for uploaded file")


def promote_to_blob_store(
    *,
    paths: BlobStorePaths,
    tenant_id: str,
    audit_id: str,
    upload_session_id: str,
    filename: str,
    content_type: str,
    sha256: str,
    byte_size: int,
    temp_file_path: Path,
) -> Dict[str, object]:
    validate_upload_candidate(
        temp_file_path=temp_file_path,
        expected_content_type=content_type,
        expected_sha256=sha256,
        expected_byte_size=byte_size,
    )

    safe_name = _safe_filename(filename)
    blob_id = f"{tenant_id}:{audit_id}:{sha256[:16]}"
    object_dir = paths.objects_dir / tenant_id / audit_id
    object_dir.mkdir(parents=True, exist_ok=True)
    object_path = object_dir / f"{sha256}_{safe_name}"

    if object_path.exists():
        object_sha = _sha256_file(object_path)
        if object_sha != sha256:
            raise ValueError("Blob store checksum collision detected")
    else:
        temp_target = object_path.with_suffix(object_path.suffix + ".tmp")
        shutil.copyfile(temp_file_path, temp_target)
        copied_sha = _sha256_file(temp_target)
        if copied_sha != sha256:
            temp_target.unlink(missing_ok=True)
            raise ValueError("Blob promotion checksum mismatch")
        os.replace(temp_target, object_path)

    manifest = {
        "blob_id": blob_id,
        "tenant_id": tenant_id,
        "audit_id": audit_id,
        "upload_session_id": upload_session_id,
        "filename": filename,
        "safe_filename": safe_name,
        "content_type": content_type,
        "sha256": sha256,
        "byte_size": byte_size,
        "storage_path": str(object_path),
    }

    paths.manifests_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = paths.manifests_dir / f"{blob_id.replace(':', '_')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "blob_id": blob_id,
        "storage_path": str(object_path),
        "manifest_path": str(manifest_path),
    }
