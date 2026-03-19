from __future__ import annotations

import csv
import io
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_registry_service import (
    DEFAULT_DATASET_ROOT,
    load_dataset_registry,
    validate_dataset_manifest,
)

TOKEN_RE = re.compile(r"[A-Za-z0-9_:.#/-]+")

SUPPORTED_CONTENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
}

ALLOWED_LOADER_KINDS = {
    "file_manifest",
    "url_manifest",
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


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.json")
        if path.is_file() and "_ingested" not in path.parts
    )


def _tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _dataset_dir(dataset_id: str, root: Path = DEFAULT_DATASET_ROOT) -> Path:
    return root / "_ingested" / _require_non_empty_str(dataset_id, "dataset_id")


def _artifact_paths(dataset_id: str, root: Path = DEFAULT_DATASET_ROOT) -> dict[str, Path]:
    base = _dataset_dir(dataset_id, root)
    return {
        "root": base,
        "normalized_text": base / "normalized_text.txt",
        "chunks": base / "chunks.json",
        "index": base / "retrieval_index.json",
        "status": base / "ingestion_status.json",
    }


def _find_manifest_path(dataset_id: str, root: Path = DEFAULT_DATASET_ROOT) -> Path:
    dataset_id = _require_non_empty_str(dataset_id, "dataset_id")
    for path in _iter_json_files(root):
        try:
            payload = _load_json(path)
            record = validate_dataset_manifest(payload, path)
            if record.dataset_id == dataset_id:
                return path
        except Exception:
            continue
    raise FileNotFoundError(f"dataset manifest not found: {dataset_id}")


def _read_local_content(content_path: Path) -> str:
    if not content_path.exists():
        raise FileNotFoundError(f"dataset content file not found: {content_path}")

    extension = content_path.suffix.lower().strip()
    if extension not in SUPPORTED_CONTENT_EXTENSIONS:
        raise ValueError(f"unsupported dataset content extension: {extension}")

    raw = content_path.read_bytes()

    if extension in {".txt", ".md"}:
        return raw.decode("utf-8").strip()
    if extension == ".json":
        payload = json.loads(raw.decode("utf-8"))
        return json.dumps(payload, indent=2, sort_keys=True)
    if extension == ".csv":
        text = raw.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        return "\n".join([", ".join(map(str, row)) for row in rows]).strip()

    raise ValueError(f"unsupported dataset content extension: {extension}")


def _read_url_manifest_text(record: Any) -> str:
    source_url = _require_non_empty_str(getattr(record, "source_url", None), "source_url")
    return (
        "URL SOURCE MANIFEST\n"
        f"dataset_id: {getattr(record, 'dataset_id', '')}\n"
        f"title: {getattr(record, 'title', '')}\n"
        f"domain: {getattr(record, 'domain', '')}\n"
        f"dataset_type: {getattr(record, 'dataset_type', '')}\n"
        f"framework_ids: {', '.join(getattr(record, 'framework_ids', []))}\n"
        f"jurisdictions: {', '.join(getattr(record, 'jurisdictions', []))}\n"
        f"countries: {', '.join(getattr(record, 'countries', []))}\n"
        f"source_url: {source_url}\n"
        f"ingested_at: {utc_now_iso()}\n"
        "fetch_mode: metadata_only\n"
    )


def _split_text_into_chunks(
    *,
    text: str,
    chunk_token_target: int = 220,
    chunk_overlap: int = 40,
) -> list[dict[str, Any]]:
    if chunk_token_target <= 0:
        raise ValueError("chunk_token_target must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_token_target:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_token_target")

    tokens = _tokenize(text)
    if not tokens:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(len(tokens), start + chunk_token_target)
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens).strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_id": f"chunk_{idx:04d}",
                    "token_start": start,
                    "token_end": end,
                    "token_count": len(chunk_tokens),
                    "text": chunk_text,
                }
            )
        if end >= len(tokens):
            break
        start = end - chunk_overlap
        idx += 1
    return chunks


def _build_retrieval_index(dataset_id: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    df_counter: Counter[str] = Counter()

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text", ""))
        for token in set(_tokenize(text)):
            df_counter[token] += 1

    return {
        "dataset_id": dataset_id,
        "chunk_count": len(chunks),
        "document_frequency": dict(sorted(df_counter.items())),
        "chunks": chunks,
    }


def _write_back_retrieval_ready_flag(
    *,
    dataset_id: str,
    retrieval_ready: bool,
    root: Path = DEFAULT_DATASET_ROOT,
) -> None:
    manifest_path = _find_manifest_path(dataset_id, root)
    payload = _load_json(manifest_path)
    retrieval = payload.get("retrieval")
    if retrieval is None:
        retrieval = {}
    retrieval = _require_dict(retrieval, "dataset_manifest.retrieval")
    retrieval["ready"] = retrieval_ready
    retrieval["last_ingested_at"] = utc_now_iso()
    payload["retrieval"] = retrieval
    _atomic_write_json(manifest_path, payload)


def ingest_dataset(
    *,
    dataset_id: str,
    chunk_token_target: int = 220,
    chunk_overlap: int = 40,
    root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    manifest_path = _find_manifest_path(dataset_id, root)
    manifest_payload = _load_json(manifest_path)
    record = validate_dataset_manifest(manifest_payload, manifest_path)

    if record.loader_kind not in ALLOWED_LOADER_KINDS:
        raise ValueError(f"unsupported loader_kind: {record.loader_kind}")

    if record.loader_kind == "file_manifest":
        if not record.content_path:
            raise ValueError("file_manifest requires content_path")
        raw_text = _read_local_content(Path(record.content_path))
    else:
        if not record.source_url:
            raise ValueError("url_manifest requires source_url")
        raw_text = _read_url_manifest_text(record)

    if not raw_text.strip():
        raise ValueError("normalized dataset text is empty")

    chunks = _split_text_into_chunks(
        text=raw_text,
        chunk_token_target=chunk_token_target,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        raise ValueError("dataset ingestion produced zero chunks")

    index = _build_retrieval_index(record.dataset_id, chunks)
    paths = _artifact_paths(record.dataset_id, root)

    _atomic_write_text(paths["normalized_text"], raw_text.rstrip() + "\n")
    _atomic_write_json(paths["chunks"], {"dataset_id": record.dataset_id, "chunks": chunks})
    _atomic_write_json(paths["index"], index)

    status = {
        "dataset_id": record.dataset_id,
        "title": record.title,
        "domain": record.domain,
        "jurisdictions": record.jurisdictions,
        "countries": record.countries,
        "framework_ids": record.framework_ids,
        "dataset_type": record.dataset_type,
        "license_type": record.license_type,
        "status": record.status,
        "loader_kind": record.loader_kind,
        "retrieval_ready": True,
        "normalized_text_path": str(paths["normalized_text"]),
        "chunks_path": str(paths["chunks"]),
        "index_path": str(paths["index"]),
        "chunk_count": len(chunks),
        "ingested_at": utc_now_iso(),
    }
    _atomic_write_json(paths["status"], status)
    _write_back_retrieval_ready_flag(dataset_id=record.dataset_id, retrieval_ready=True, root=root)
    return status


def ingest_all_datasets(
    *,
    root: Path = DEFAULT_DATASET_ROOT,
    only_active: bool = True,
) -> dict[str, Any]:
    registry = load_dataset_registry(root)
    processed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for item in registry["items"]:
        if not isinstance(item, dict):
            continue
        if only_active and item.get("status") != "ACTIVE":
            continue
        dataset_id = item.get("dataset_id")
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            continue
        try:
            processed.append(ingest_dataset(dataset_id=dataset_id, root=root))
        except Exception as exc:
            failures.append({"dataset_id": dataset_id, "error": str(exc)})

    return {
        "processed_count": len(processed),
        "failure_count": len(failures),
        "processed": processed,
        "failures": failures,
    }


def get_dataset_ingestion_status(
    *,
    dataset_id: str,
    root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    path = _artifact_paths(dataset_id, root)["status"]
    if not path.exists():
        raise FileNotFoundError(f"dataset ingestion status not found: {dataset_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("dataset ingestion status must be object")
    return payload


def search_dataset_index(
    *,
    dataset_id: str,
    query: str,
    top_k: int = 8,
    root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    dataset_id = _require_non_empty_str(dataset_id, "dataset_id")
    query = _require_non_empty_str(query, "query")
    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be positive int")

    index_path = _artifact_paths(dataset_id, root)["index"]
    if not index_path.exists():
        raise FileNotFoundError(f"dataset retrieval index not found: {dataset_id}")
    index = _load_json(index_path)

    chunks = index.get("chunks", [])
    df = index.get("document_frequency", {})
    if not isinstance(chunks, list):
        raise ValueError("dataset retrieval chunks must be list")
    if not isinstance(df, dict):
        raise ValueError("dataset retrieval document_frequency must be object")

    query_tokens = _tokenize(query)
    total_chunks = max(1, len(chunks))
    rows: list[dict[str, Any]] = []

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text", ""))
        tf = Counter(_tokenize(text))
        score = 0.0
        for token in query_tokens:
            freq = tf.get(token, 0)
            if freq <= 0:
                continue
            doc_freq = max(1, int(df.get(token, 0)))
            score += freq * ((1 + total_chunks) / (1 + doc_freq))
        if score <= 0:
            continue
        rows.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "score": round(score, 6),
                "token_count": chunk.get("token_count"),
                "excerpt": text[:400],
            }
        )

    rows.sort(key=lambda item: (-item["score"], str(item["chunk_id"])))
    return {
        "dataset_id": dataset_id,
        "query": query,
        "result_count": min(top_k, len(rows)),
        "results": rows[:top_k],
    }
