from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.evidence_pack_service import EvidencePackPaths, get_evidence_pack
from core.evidence_processing_service import _load_index as _load_evidence_index


DEFAULT_PACK_ROOT = Path("artifacts") / "evidence_packs"
TOKEN_RE = re.compile(r"[A-Za-z0-9_:.#/-]+")


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
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


def _tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def _safe_excerpt(text: str, needle_tokens: list[str], max_chars: int = 400) -> str:
    if not text:
        return ""
    lowered = text.lower()
    pos = -1
    for token in needle_tokens:
        pos = lowered.find(token.lower())
        if pos >= 0:
            break
    if pos < 0:
        return text[:max_chars].strip()

    start = max(0, pos - max_chars // 3)
    end = min(len(text), start + max_chars)
    return text[start:end].strip()


def _processing_root(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "processing"


def _retrieval_root(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "retrieval"


def _retrieval_index_path(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return _retrieval_root(pack_id, pack_root) / "index.json"


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: str
    evidence_id: str
    filename: str
    title: str
    source_type: str
    text: str
    token_count: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "evidence_id": self.evidence_id,
            "filename": self.filename,
            "title": self.title,
            "source_type": self.source_type,
            "text": self.text,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


def _split_text_into_chunks(
    *,
    evidence_id: str,
    filename: str,
    title: str,
    source_type: str,
    text: str,
    chunk_token_target: int = 180,
    chunk_overlap: int = 40,
) -> list[RetrievalChunk]:
    tokens = _tokenize(text)
    if not tokens:
        return []

    if chunk_token_target <= 0:
        raise ValueError("chunk_token_target must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_token_target:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_token_target")

    chunks: list[RetrievalChunk] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(len(tokens), start + chunk_token_target)
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens).strip()
        if chunk_text:
            chunks.append(
                RetrievalChunk(
                    chunk_id=f"{evidence_id}::chunk_{idx:04d}",
                    evidence_id=evidence_id,
                    filename=filename,
                    title=title,
                    source_type=source_type,
                    text=chunk_text,
                    token_count=len(chunk_tokens),
                    metadata={
                        "token_start": start,
                        "token_end": end,
                    },
                )
            )
        if end >= len(tokens):
            break
        start = end - chunk_overlap
        idx += 1
    return chunks


def build_pack_retrieval_index(
    *,
    pack_id: str,
    pack_root: Path = DEFAULT_PACK_ROOT,
    chunk_token_target: int = 180,
    chunk_overlap: int = 40,
) -> dict[str, Any]:
    get_evidence_pack(pack_id, pack_root=pack_root)
    evidence_index = _load_evidence_index(pack_id, pack_root=pack_root)
    items = evidence_index.get("items", [])
    if not isinstance(items, list):
        raise ValueError("evidence_index.items must be a list")

    _processing_root(pack_id, pack_root).mkdir(parents=True, exist_ok=True)
    all_chunks: list[RetrievalChunk] = []
    document_rows: list[dict[str, Any]] = []

    for row in items:
        if not isinstance(row, dict):
            continue
        if row.get("processing_status") != "READY":
            continue

        evidence_id = _require_non_empty_str(row.get("evidence_id"), "evidence_id")
        filename = _require_non_empty_str(row.get("filename"), "filename")
        title = _require_non_empty_str(row.get("title"), "title")
        source_type = _require_non_empty_str(row.get("source_type"), "source_type")
        extracted_text_path = row.get("extracted_text_path")
        if not isinstance(extracted_text_path, str) or not extracted_text_path.strip():
            continue

        text_path = Path(extracted_text_path)
        if not text_path.exists():
            continue
        extracted_text = text_path.read_text(encoding="utf-8").strip()
        if not extracted_text:
            continue

        chunks = _split_text_into_chunks(
            evidence_id=evidence_id,
            filename=filename,
            title=title,
            source_type=source_type,
            text=extracted_text,
            chunk_token_target=chunk_token_target,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)

        document_rows.append(
            {
                "evidence_id": evidence_id,
                "filename": filename,
                "title": title,
                "source_type": source_type,
                "chunk_count": len(chunks),
                "classification": row.get("classification"),
                "key_facts": row.get("key_facts"),
            }
        )

    df_counter: Counter[str] = Counter()
    chunk_rows: list[dict[str, Any]] = []
    for chunk in all_chunks:
        tokens = _tokenize(chunk.text)
        for token in set(tokens):
            df_counter[token] += 1
        chunk_rows.append(chunk.to_dict())

    index_payload = {
        "pack_id": pack_id,
        "chunk_token_target": chunk_token_target,
        "chunk_overlap": chunk_overlap,
        "document_count": len(document_rows),
        "chunk_count": len(chunk_rows),
        "documents": document_rows,
        "chunks": chunk_rows,
        "document_frequency": dict(sorted(df_counter.items())),
    }

    _atomic_write_json(_retrieval_index_path(pack_id, pack_root), index_payload)
    return index_payload


def load_pack_retrieval_index(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    path = _retrieval_index_path(pack_id, pack_root)
    if not path.exists():
        raise FileNotFoundError(f"retrieval index not found for pack: {pack_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("retrieval index must be object")
    return payload


def _score_chunk(
    *,
    query_tokens: list[str],
    chunk_text: str,
    df: dict[str, int],
    total_chunks: int,
) -> float:
    if not query_tokens:
        return 0.0

    tokens = _tokenize(chunk_text)
    if not tokens:
        return 0.0

    tf = Counter(tokens)
    score = 0.0
    for token in query_tokens:
        freq = tf.get(token, 0)
        if freq == 0:
            continue
        doc_freq = max(1, int(df.get(token, 0)))
        idf = math.log((1 + total_chunks) / (1 + doc_freq)) + 1.0
        score += freq * idf
    return round(score, 6)


def search_pack_corpus(
    *,
    pack_id: str,
    query: str,
    top_k: int = 8,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    query = _require_non_empty_str(query, "query")
    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be positive int")

    index = load_pack_retrieval_index(pack_id, pack_root=pack_root)
    chunks = index.get("chunks", [])
    df = index.get("document_frequency", {})
    if not isinstance(chunks, list):
        raise ValueError("retrieval index chunks must be list")
    if not isinstance(df, dict):
        raise ValueError("retrieval index document_frequency must be object")

    query_tokens = _tokenize(query)
    total_chunks = max(1, len(chunks))

    scored = []
    for row in chunks:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text", ""))
        score = _score_chunk(
            query_tokens=query_tokens,
            chunk_text=text,
            df=df,
            total_chunks=total_chunks,
        )
        if score <= 0:
            continue
        scored.append(
            {
                "chunk_id": row.get("chunk_id"),
                "evidence_id": row.get("evidence_id"),
                "filename": row.get("filename"),
                "title": row.get("title"),
                "source_type": row.get("source_type"),
                "score": score,
                "excerpt": _safe_excerpt(text, query_tokens),
                "metadata": row.get("metadata", {}),
            }
        )

    scored.sort(key=lambda x: (-x["score"], str(x["chunk_id"])))
    return {
        "pack_id": pack_id,
        "query": query,
        "result_count": min(top_k, len(scored)),
        "results": scored[:top_k],
    }


def build_audit_context_pack(
    *,
    pack_id: str,
    audit_questions: list[str],
    top_k_per_question: int = 5,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    if not isinstance(audit_questions, list) or not audit_questions:
        raise ValueError("audit_questions must be non-empty list[str]")

    get_evidence_pack(pack_id, pack_root=pack_root)
    context_rows = []
    seen_chunk_ids: set[str] = set()

    for idx, question in enumerate(audit_questions):
        question = _require_non_empty_str(question, f"audit_questions[{idx}]")
        result = search_pack_corpus(
            pack_id=pack_id,
            query=question,
            top_k=top_k_per_question,
            pack_root=pack_root,
        )
        selected = []
        for row in result["results"]:
            chunk_id = row["chunk_id"]
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            selected.append(row)

        context_rows.append(
            {
                "question": question,
                "matches": selected,
            }
        )

    return {
        "pack_id": pack_id,
        "question_count": len(audit_questions),
        "selected_chunk_count": len(seen_chunk_ids),
        "questions": context_rows,
    }
