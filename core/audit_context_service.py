from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.audit_planner import build_audit_plan_from_pack
from core.evidence_pack_service import EvidencePackPaths, get_evidence_pack
from core.readiness_service import build_readiness_plan
from core.retrieval_service import (
    build_audit_context_pack,
    build_pack_retrieval_index,
    load_pack_retrieval_index,
)

DEFAULT_PACK_ROOT = Path("artifacts") / "evidence_packs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _context_root(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return EvidencePackPaths.for_pack(pack_id, pack_root).root / "audit_context"


def _context_path(pack_id: str, pack_root: Path = DEFAULT_PACK_ROOT) -> Path:
    return _context_root(pack_id, pack_root) / "context_pack.json"


def _question_templates_for_control(control: dict[str, Any]) -> list[str]:
    control_id = str(control.get("control_id", "")).strip()
    title = str(control.get("title", "")).strip()
    required_evidence_types = control.get("required_evidence_types", [])
    if not isinstance(required_evidence_types, list):
        required_evidence_types = []

    questions = [
        f"What evidence supports control {control_id}?",
        f"What evidence supports {title}?",
    ]

    for evidence_type in required_evidence_types:
        if isinstance(evidence_type, str) and evidence_type.strip():
            questions.append(
                f"What evidence supports {control_id} required evidence type {evidence_type.strip()}?"
            )

    return questions


def build_default_audit_questions(
    *,
    pack_id: str,
    max_controls: int = 25,
    max_questions: int = 100,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> list[str]:
    if not isinstance(max_controls, int) or max_controls <= 0:
        raise ValueError("max_controls must be positive int")
    if not isinstance(max_questions, int) or max_questions <= 0:
        raise ValueError("max_questions must be positive int")

    plan = build_audit_plan_from_pack(pack_id, pack_root=pack_root)
    readiness = build_readiness_plan(pack_id, pack_root=pack_root)

    questions: list[str] = []
    seen: set[str] = set()

    base_questions = [
        "What evidence supports company profile and audit scope?",
        "What evidence supports governance ownership and policy coverage?",
        "What evidence supports transaction monitoring and escalation controls?",
        "What evidence supports sanctions screening and alert handling?",
        "What evidence supports customer due diligence and periodic review?",
    ]

    for q in base_questions:
        if q not in seen:
            seen.add(q)
            questions.append(q)

    selected_controls = plan.get("selected_controls", [])
    if not isinstance(selected_controls, list):
        selected_controls = []

    for control in selected_controls[:max_controls]:
        if not isinstance(control, dict):
            continue
        for q in _question_templates_for_control(control):
            if q not in seen:
                seen.add(q)
                questions.append(q)
            if len(questions) >= max_questions:
                break
        if len(questions) >= max_questions:
            break

    requested_actions = readiness.get("requested_evidence_actions", [])
    if isinstance(requested_actions, list):
        for row in requested_actions:
            if not isinstance(row, dict):
                continue
            control_id = str(row.get("control_id", "")).strip()
            title = str(row.get("title", "")).strip()
            reqs = row.get("request_evidence_types", [])
            if not isinstance(reqs, list):
                reqs = []
            for evidence_type in reqs:
                if not isinstance(evidence_type, str) or not evidence_type.strip():
                    continue
                q = (
                    f"What evidence is missing for control {control_id} "
                    f"({title}) regarding {evidence_type.strip()}?"
                )
                if q not in seen:
                    seen.add(q)
                    questions.append(q)
                if len(questions) >= max_questions:
                    break
            if len(questions) >= max_questions:
                break

    return questions[:max_questions]


def build_retrieval_grounded_context_pack(
    *,
    pack_id: str,
    audit_questions: list[str] | None = None,
    top_k_per_question: int = 5,
    ensure_retrieval_index: bool = True,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    pack = get_evidence_pack(pack_id, pack_root=pack_root)
    manifest = pack["manifest"]
    detail = pack["detail"]

    if ensure_retrieval_index:
        try:
            retrieval_index = load_pack_retrieval_index(pack_id=pack_id, pack_root=pack_root)
        except FileNotFoundError:
            retrieval_index = build_pack_retrieval_index(pack_id=pack_id, pack_root=pack_root)
    else:
        retrieval_index = load_pack_retrieval_index(pack_id=pack_id, pack_root=pack_root)

    plan = build_audit_plan_from_pack(pack_id, pack_root=pack_root)
    readiness = build_readiness_plan(pack_id, pack_root=pack_root)

    resolved_questions = audit_questions or build_default_audit_questions(
        pack_id=pack_id,
        pack_root=pack_root,
    )

    if not isinstance(resolved_questions, list) or not resolved_questions:
        raise ValueError("audit_questions must be a non-empty list[str]")

    normalized_questions: list[str] = []
    for idx, value in enumerate(resolved_questions):
        normalized_questions.append(_require_non_empty_str(value, f"audit_questions[{idx}]"))

    retrieval_context = build_audit_context_pack(
        pack_id=pack_id,
        audit_questions=normalized_questions,
        top_k_per_question=top_k_per_question,
        pack_root=pack_root,
    )

    context_pack = {
        "pack_id": detail["pack_id"],
        "pack_name": detail["name"],
        "generated_at": utc_now_iso(),
        "deterministic_authoritative": True,
        "company_profile": manifest.get("company_profile", {}),
        "scope": manifest.get("scope", {}),
        "plan_summary": {
            "selected_control_count": plan.get("selected_control_count"),
            "excluded_control_count": plan.get("excluded_control_count"),
        },
        "readiness_summary": readiness.get("summary", {}),
        "corpus_readiness": readiness.get("corpus_readiness", {}),
        "retrieval_index_summary": {
            "document_count": retrieval_index.get("document_count"),
            "chunk_count": retrieval_index.get("chunk_count"),
        },
        "questions": retrieval_context["questions"],
        "selected_chunk_count": retrieval_context["selected_chunk_count"],
        "question_count": retrieval_context["question_count"],
    }

    _atomic_write_json(_context_path(pack_id, pack_root), context_pack)
    return context_pack


def get_context_pack(
    *,
    pack_id: str,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    path = _context_path(pack_id, pack_root)
    if not path.exists():
        raise FileNotFoundError(f"context pack not found for pack: {pack_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("context pack must be object")
    return payload
