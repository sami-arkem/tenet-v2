from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.dataset_registry_service import DEFAULT_DATASET_ROOT, validate_dataset_manifest
from core.source_acquisition_service import (
    DEFAULT_SOURCE_REGISTRY_ROOT,
    evaluate_source_for_ingestion_enhanced,
    get_source_by_id,
    load_source_registry,
)
from core.source_dataset_promotion_service import promote_source_to_dataset_manifest

DEFAULT_SOURCE_RUN_ROOT = Path("fixtures") / "source_registry" / "runs"

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".xml", ".html"}
DEFAULT_TIMEOUT_SECONDS = 30
USER_AGENT = "TenetOfficialCorpusBot/1.0 (+https://tenet.local)"
AUTHORIZED_SOURCE_CLASSES = {
    "PUBLIC_OFFICIAL",
    "LICENSED",
    "CUSTOMER_PROVIDED",
    "CONTRACT_AUTHORIZED",
}
AUTHORIZED_LICENSE_STATUSES = {
    "PUBLIC",
    "LICENSED",
    "CUSTOMER_AUTHORIZED",
    "CONTRACT_AUTHORIZED",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_slug(value: str) -> str:
    value = _require_non_empty_str(value, "value")
    chars: list[str] = []
    for ch in value.lower():
        chars.append(ch if ch.isalnum() else "_")
    slug = "".join(chars).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    if not slug:
        raise ValueError("slug became empty")
    return slug


@dataclass(frozen=True)
class SourceRunPaths:
    run_root: Path
    snapshots_root: Path
    raw_bytes_path: Path
    normalized_text_path: Path
    metadata_path: Path
    ledger_path: Path
    dataset_manifest_path: Path
    dataset_content_path: Path
    latest_snapshot_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "run_root": str(self.run_root),
            "snapshots_root": str(self.snapshots_root),
            "raw_bytes_path": str(self.raw_bytes_path),
            "normalized_text_path": str(self.normalized_text_path),
            "metadata_path": str(self.metadata_path),
            "ledger_path": str(self.ledger_path),
            "dataset_manifest_path": str(self.dataset_manifest_path),
            "dataset_content_path": str(self.dataset_content_path),
            "latest_snapshot_path": str(self.latest_snapshot_path),
        }


def _run_paths(source_id: str, root: Path = DEFAULT_SOURCE_RUN_ROOT) -> SourceRunPaths:
    run_root = root / _safe_slug(source_id)
    return SourceRunPaths(
        run_root=run_root,
        snapshots_root=run_root / "snapshots",
        raw_bytes_path=run_root / "raw_source.bin",
        normalized_text_path=run_root / "normalized_text.txt",
        metadata_path=run_root / "fetch_metadata.json",
        ledger_path=run_root / "run_ledger.json",
        dataset_manifest_path=run_root / "promoted_dataset_manifest.json",
        dataset_content_path=run_root / "promoted_dataset_content.txt",
        latest_snapshot_path=run_root / "latest_snapshot.json",
    )


def _find_source_manifest(source_id: str, source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT) -> tuple[Path, dict[str, Any]]:
    source = get_source_by_id(source_id, source_root)
    if source is None:
        raise FileNotFoundError(f"source manifest not found: {source_id}")
    metadata = _require_dict(source.get("metadata", {}), "source.metadata")
    manifest_path = Path(_require_non_empty_str(metadata.get("manifest_path"), "source.metadata.manifest_path"))
    return manifest_path, _load_json(manifest_path)


def _is_fetch_eligible_source(source: dict[str, Any]) -> bool:
    if not isinstance(source, dict):
        return False
    if source.get("approved") is not True:
        return False
    if source.get("retrieval_allowed") is not True:
        return False
    if source.get("source_class") not in AUTHORIZED_SOURCE_CLASSES:
        return False
    if source.get("license_status") not in AUTHORIZED_LICENSE_STATUSES:
        return False
    source_url = source.get("source_url")
    return isinstance(source_url, str) and bool(source_url.strip())


def _append_run_ledger(path: Path, entry: dict[str, Any]) -> None:
    payload: dict[str, Any]
    if path.exists():
        payload = _load_json(path)
    else:
        payload = {"entries": []}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("run ledger entries must be a list")
    entries.append(entry)
    payload["entries"] = entries
    payload["entry_count"] = len(entries)
    payload["latest_fetched_at"] = entry["fetched_at"]
    _atomic_write_json(path, payload)


def _write_versioned_snapshot(
    *,
    paths: SourceRunPaths,
    source_id: str,
    raw_bytes: bytes,
    normalized_text: str,
    metadata: dict[str, Any],
) -> dict[str, str]:
    snapshot_id = f"{metadata['fetched_at'].replace(':', '').replace('+', '_')}_{metadata['raw_sha256'][:12]}"
    snapshot_root = paths.snapshots_root / snapshot_id
    raw_path = snapshot_root / "raw_source.bin"
    text_path = snapshot_root / "normalized_text.txt"
    metadata_path = snapshot_root / "fetch_metadata.json"
    _atomic_write_bytes(raw_path, raw_bytes)
    _atomic_write_text(text_path, normalized_text.rstrip() + "\n")
    _atomic_write_json(metadata_path, metadata)
    latest_snapshot = {
        "source_id": source_id,
        "snapshot_id": snapshot_id,
        "snapshot_root": str(snapshot_root),
        "raw_path": str(raw_path),
        "normalized_text_path": str(text_path),
        "metadata_path": str(metadata_path),
        "fetched_at": metadata["fetched_at"],
        "raw_sha256": metadata["raw_sha256"],
    }
    _atomic_write_json(paths.latest_snapshot_path, latest_snapshot)
    return latest_snapshot


def _normalize_bytes_to_text(raw: bytes, source_url: str | None, filename_hint: str | None = None) -> str:
    hint = (filename_hint or "").lower()
    parsed_path = urlparse(source_url).path.lower() if isinstance(source_url, str) else ""
    extension = Path(hint or parsed_path).suffix.lower()

    if extension not in SUPPORTED_TEXT_EXTENSIONS:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    if extension in {".txt", ".md", ".xml", ".html"}:
        return raw.decode("utf-8", errors="replace")
    if extension == ".json":
        payload = json.loads(raw.decode("utf-8"))
        return json.dumps(payload, indent=2, sort_keys=True)
    if extension == ".csv":
        text = raw.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        return "\n".join([", ".join(map(str, row)) for row in rows]).strip()

    return raw.decode("utf-8", errors="replace")


def _fetch_public_url(source_url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[bytes, dict[str, Any]]:
    source_url = _require_non_empty_str(source_url, "source_url")
    request = Request(
        source_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        content = response.read()
        metadata = {
            "status_code": getattr(response, "status", None),
            "content_type": response.headers.get("Content-Type"),
            "content_length_header": response.headers.get("Content-Length"),
            "final_url": response.geturl(),
        }
    return content, metadata


def _write_promoted_dataset_content(*, dataset_manifest_path: Path, normalized_text: str) -> None:
    dataset_manifest = _load_json(dataset_manifest_path)
    loader = _require_dict(dataset_manifest.get("loader"), "dataset_manifest.loader")
    kind = _require_non_empty_str(loader.get("kind"), "dataset_manifest.loader.kind")

    if kind != "file_manifest":
        return

    content_path = loader.get("content_path")
    if not isinstance(content_path, str) or not content_path.strip():
        raise ValueError("promoted file_manifest dataset requires loader.content_path")

    resolved = (dataset_manifest_path.parent / content_path).resolve()
    _atomic_write_text(resolved, normalized_text.rstrip() + "\n")


def fetch_real_source_to_dataset(
    *,
    source_id: str,
    source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    run_root: Path = DEFAULT_SOURCE_RUN_ROOT,
    force_file_manifest: bool = True,
) -> dict[str, Any]:
    source_id = _require_non_empty_str(source_id, "source_id")

    evaluation = evaluate_source_for_ingestion_enhanced(source_id=source_id, root=source_root)
    if evaluation["decision"] != "APPROVE":
        raise ValueError(
            "source blocked from fetch pipeline; reasons: "
            + ", ".join(evaluation.get("reasons", []))
        )

    source_manifest_path, source_manifest = _find_source_manifest(source_id, source_root)
    if not _is_fetch_eligible_source(source_manifest):
        raise ValueError("source blocked from fetch pipeline; source manifest is not fetch-eligible")
    source_url = source_manifest.get("source_url")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError("real source fetch requires source_url")

    raw_bytes, fetch_meta = _fetch_public_url(source_url)
    if not raw_bytes:
        raise ValueError("fetched empty response body")

    normalized_text = _normalize_bytes_to_text(raw_bytes, source_url=source_url)
    if not normalized_text.strip():
        raise ValueError("normalized fetched text is empty")

    paths = _run_paths(source_id, run_root)
    _atomic_write_bytes(paths.raw_bytes_path, raw_bytes)
    _atomic_write_text(paths.normalized_text_path, normalized_text.rstrip() + "\n")

    promoted = promote_source_to_dataset_manifest(
        source_id=source_id,
        source_root=source_root,
        dataset_root=dataset_root,
        write_stub_content_for_file_manifest=False,
    )

    promoted_manifest_path = Path(promoted["dataset_manifest_path"])
    promoted_manifest = _load_json(promoted_manifest_path)
    if force_file_manifest:
        promoted_manifest["loader"] = {
            "kind": "file_manifest",
            "content_path": f"{_safe_slug(source_id)}.txt",
        }
        promoted_manifest["retrieval"] = {"ready": False}
        _atomic_write_json(promoted_manifest_path, promoted_manifest)

    _write_promoted_dataset_content(
        dataset_manifest_path=promoted_manifest_path,
        normalized_text=normalized_text,
    )

    validated = validate_dataset_manifest(_load_json(promoted_manifest_path), promoted_manifest_path)

    metadata = {
        "source_id": source_id,
        "source_manifest_path": str(source_manifest_path),
        "fetched_at": utc_now_iso(),
        "source_url": source_url,
        "raw_sha256": _sha256_bytes(raw_bytes),
        "raw_size_bytes": len(raw_bytes),
        "normalized_text_chars": len(normalized_text),
        "fetch_meta": fetch_meta,
        "provenance_checks": evaluation.get("provenance_checks"),
        "dataset_manifest_path": str(promoted_manifest_path),
        "dataset_id": validated.dataset_id,
        "deterministic_authoritative": True,
    }
    latest_snapshot = _write_versioned_snapshot(
        paths=paths,
        source_id=source_id,
        raw_bytes=raw_bytes,
        normalized_text=normalized_text,
        metadata=metadata,
    )
    metadata["latest_snapshot"] = latest_snapshot
    _atomic_write_json(paths.metadata_path, metadata)
    _atomic_write_json(paths.dataset_manifest_path, _load_json(promoted_manifest_path))
    _atomic_write_text(paths.dataset_content_path, normalized_text.rstrip() + "\n")
    _append_run_ledger(
        paths.ledger_path,
        {
            "source_id": source_id,
            "dataset_id": validated.dataset_id,
            "fetched_at": metadata["fetched_at"],
            "raw_sha256": metadata["raw_sha256"],
            "raw_size_bytes": metadata["raw_size_bytes"],
            "snapshot_id": latest_snapshot["snapshot_id"],
            "snapshot_root": latest_snapshot["snapshot_root"],
            "source_url": source_url,
        },
    )

    return {
        "source_id": source_id,
        "dataset_id": validated.dataset_id,
        "fetch_metadata": metadata,
        "paths": paths.to_dict(),
        "deterministic_authoritative": True,
    }


def fetch_all_allowed_real_sources(
    *,
    source_root: Path = DEFAULT_SOURCE_REGISTRY_ROOT,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    run_root: Path = DEFAULT_SOURCE_RUN_ROOT,
) -> dict[str, Any]:
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for payload in load_source_registry(source_root)["items"]:
        if not isinstance(payload, dict):
            continue
        if not _is_fetch_eligible_source(payload):
            continue
        source_id = payload.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue

        try:
            evaluation = evaluate_source_for_ingestion_enhanced(source_id=source_id, root=source_root)
            if evaluation["decision"] != "APPROVE":
                continue

            successes.append(
                fetch_real_source_to_dataset(
                    source_id=source_id,
                    source_root=source_root,
                    dataset_root=dataset_root,
                    run_root=run_root,
                )
            )
        except Exception as exc:
            failures.append({"source_id": source_id, "error": str(exc)})

    return {
        "success_count": len(successes),
        "failure_count": len(failures),
        "successes": successes,
        "failures": failures,
        "deterministic_authoritative": True,
    }
