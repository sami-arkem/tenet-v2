from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from api.store import execute_and_store_audit
from core.audit_context_service import build_retrieval_grounded_context_pack, get_context_pack
from core.audit_planner import build_execution_payload_from_pack
from core.evidence_pack_service import EvidencePackPaths, get_evidence_pack
from core.evidence_processing_service import build_corpus_readiness

DEFAULT_PACK_ROOT = Path("artifacts") / "evidence_packs"
DEFAULT_WORKFLOW_ROOT = Path("artifacts") / "workflow_runs"


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


def _workflow_detail_path(workflow_id: str, workflow_root: Path = DEFAULT_WORKFLOW_ROOT) -> Path:
    workflow_id = _require_non_empty_str(workflow_id, "workflow_id")
    return workflow_root / workflow_id / "detail.json"


def _append_timeline(detail: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
    detail.setdefault("timeline", [])
    detail["timeline"].append(
        {
            "created_at": utc_now_iso(),
            "event_type": event_type,
            "payload": payload,
        }
    )
    detail["updated_at"] = utc_now_iso()


def ensure_context_pack_ready(
    *,
    pack_id: str,
    ensure_built: bool = True,
    top_k_per_question: int = 5,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    _require_non_empty_str(pack_id, "pack_id")
    get_evidence_pack(pack_id, pack_root=pack_root)

    corpus = build_corpus_readiness(pack_id, pack_root=pack_root)
    if corpus["corpus_ready"] is not True:
        raise ValueError("evidence corpus is not ready for context-gated execution")

    try:
        ctx = get_context_pack(pack_id=pack_id, pack_root=pack_root)
    except FileNotFoundError:
        if ensure_built is not True:
            raise
        ctx = build_retrieval_grounded_context_pack(
            pack_id=pack_id,
            top_k_per_question=top_k_per_question,
            ensure_retrieval_index=True,
            pack_root=pack_root,
        )

    if not isinstance(ctx, dict):
        raise ValueError("context pack must be object")
    if ctx.get("deterministic_authoritative") is not True:
        raise ValueError("context pack must be deterministic_authoritative=true")
    if not isinstance(ctx.get("questions"), list) or not ctx["questions"]:
        raise ValueError("context pack must contain non-empty questions")
    if int(ctx.get("selected_chunk_count", 0)) <= 0:
        raise ValueError("context pack must include selected retrieval chunks")

    return ctx


def build_execution_payload_from_context(
    *,
    pack_id: str,
    context_pack: dict[str, Any],
    run_id: str,
    default_remediation_owner: str,
    metadata: dict[str, Any] | None = None,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    run_id = _require_non_empty_str(run_id, "run_id")
    default_remediation_owner = _require_non_empty_str(default_remediation_owner, "default_remediation_owner")
    get_evidence_pack(pack_id, pack_root=pack_root)

    base_payload = build_execution_payload_from_pack(pack_id, pack_root=pack_root)

    payload = deepcopy(base_payload)
    payload["run_id"] = run_id
    payload["default_remediation_owner"] = default_remediation_owner
    payload["metadata"] = {
        **payload.get("metadata", {}),
        **(metadata or {}),
        "context_gated_execution": True,
        "context_pack_present": True,
        "context_question_count": context_pack.get("question_count"),
        "context_selected_chunk_count": context_pack.get("selected_chunk_count"),
    }
    payload["audit_context_pack"] = context_pack
    return payload


def execute_pack_via_context(
    *,
    pack_id: str,
    run_id: str,
    default_remediation_owner: str,
    metadata: dict[str, Any] | None = None,
    export: dict[str, Any] | None = None,
    top_k_per_question: int = 5,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    context_pack = ensure_context_pack_ready(
        pack_id=pack_id,
        ensure_built=True,
        top_k_per_question=top_k_per_question,
        pack_root=pack_root,
    )

    payload = build_execution_payload_from_context(
        pack_id=pack_id,
        context_pack=context_pack,
        run_id=run_id,
        default_remediation_owner=default_remediation_owner,
        metadata=metadata,
        pack_root=pack_root,
    )

    execution_detail = execute_and_store_audit(
        payload=payload,
        export=export,
    )

    return {
        "pack_id": pack_id,
        "run_id": execution_detail["run_id"],
        "context_pack": context_pack,
        "execution": execution_detail,
    }


def execute_workflow_via_context(
    *,
    workflow_id: str,
    run_id: str,
    default_remediation_owner: str,
    metadata: dict[str, Any] | None = None,
    export: dict[str, Any] | None = None,
    workflow_root: Path = DEFAULT_WORKFLOW_ROOT,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    path = _workflow_detail_path(workflow_id, workflow_root)
    if not path.exists():
        raise FileNotFoundError(f"workflow not found: {workflow_id}")

    workflow = _load_json(path)
    if not isinstance(workflow, dict):
        raise ValueError("workflow detail must be object")

    pack_id = _require_non_empty_str(workflow.get("pack_id"), "workflow.pack_id")

    out = execute_pack_via_context(
        pack_id=pack_id,
        run_id=run_id,
        default_remediation_owner=default_remediation_owner,
        metadata={
            **(metadata or {}),
            "workflow_id": workflow_id,
        },
        export=export,
        pack_root=pack_root,
    )

    workflow["status"] = "AUDIT_EXECUTED"
    workflow["latest_context_pack"] = {
        "question_count": out["context_pack"]["question_count"],
        "selected_chunk_count": out["context_pack"]["selected_chunk_count"],
        "generated_at": out["context_pack"]["generated_at"],
    }
    workflow["latest_execution"] = out["execution"]
    _append_timeline(
        workflow,
        "context_gated_audit_executed",
        {
            "run_id": out["run_id"],
            "question_count": out["context_pack"]["question_count"],
            "selected_chunk_count": out["context_pack"]["selected_chunk_count"],
            "deployment_decision": out["execution"]["topline"]["deployment_decision"],
        },
    )
    _atomic_write_json(path, workflow)

    return workflow
