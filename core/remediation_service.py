from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_STORE_ROOT = Path("artifacts") / "audit_runs"


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


@dataclass(frozen=True)
class AuditRunPaths:
    root: Path
    detail_path: Path
    remediation_state_path: Path

    @staticmethod
    def for_run(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> "AuditRunPaths":
        run_id = _require_non_empty_str(run_id, "run_id")
        root = store_root / run_id
        return AuditRunPaths(
            root=root,
            detail_path=root / "detail.json",
            remediation_state_path=root / "remediation_state.json",
        )


def _ensure_audit_exists(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> AuditRunPaths:
    paths = AuditRunPaths.for_run(run_id, store_root)
    if not paths.detail_path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    return paths


def _load_detail(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    paths = _ensure_audit_exists(run_id, store_root)
    return _load_json(paths.detail_path)


def _build_initial_remediation_state(detail: dict[str, Any]) -> dict[str, Any]:
    remediation_items = detail.get("deterministic_audit_result", {}).get("remediation_items", [])
    if not isinstance(remediation_items, list):
        raise ValueError("deterministic_audit_result.remediation_items must be a list")

    now = utc_now_iso()
    items: list[dict[str, Any]] = []
    for row in remediation_items:
        if not isinstance(row, dict):
            raise ValueError("remediation item must be an object")
        item = deepcopy(row)
        item.setdefault("evidence_links", [])
        item.setdefault("comment_history", [])
        item["created_at"] = now
        item["updated_at"] = now
        item["status_source"] = "deterministic_seed"
        items.append(item)

    return {
        "run_id": detail.get("run_id"),
        "generated_at": now,
        "updated_at": now,
        "items": items,
    }


def ensure_remediation_state(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    paths = _ensure_audit_exists(run_id, store_root)
    if paths.remediation_state_path.exists():
        return _load_json(paths.remediation_state_path)

    detail = _load_detail(run_id, store_root)
    state = _build_initial_remediation_state(detail)
    _atomic_write_json(paths.remediation_state_path, state)
    return state


def reseed_remediation_state(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    detail = _load_detail(run_id, store_root)
    state = _build_initial_remediation_state(detail)
    paths = AuditRunPaths.for_run(run_id, store_root)
    _atomic_write_json(paths.remediation_state_path, state)
    return state


def list_remediations(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> list[dict[str, Any]]:
    state = ensure_remediation_state(run_id, store_root)
    items = state.get("items", [])
    if not isinstance(items, list):
        raise ValueError("remediation_state.items must be a list")
    return items


def get_remediation(run_id: str, remediation_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    remediation_id = _require_non_empty_str(remediation_id, "remediation_id")
    items = list_remediations(run_id, store_root)
    for row in items:
        if row.get("remediation_id") == remediation_id:
            return row
    raise FileNotFoundError(f"remediation item not found: {remediation_id}")


def update_remediation(
    *,
    run_id: str,
    remediation_id: str,
    owner: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
    action_required: str | None = None,
    note: str | None = None,
    evidence_links: list[str] | None = None,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    remediation_id = _require_non_empty_str(remediation_id, "remediation_id")
    state = ensure_remediation_state(run_id, store_root)
    items = state.get("items", [])
    if not isinstance(items, list):
        raise ValueError("remediation_state.items must be a list")

    found = None
    for row in items:
        if row.get("remediation_id") == remediation_id:
            found = row
            break

    if found is None:
        raise FileNotFoundError(f"remediation item not found: {remediation_id}")

    if owner is not None:
        found["owner"] = _require_non_empty_str(owner, "owner")
    if due_date is not None:
        found["due_date"] = _require_non_empty_str(due_date, "due_date")
    if status is not None:
        found["status"] = _require_non_empty_str(status, "status")
        found["status_source"] = "manual_update"
    if action_required is not None:
        found["action_required"] = _require_non_empty_str(action_required, "action_required")
    if evidence_links is not None:
        if not isinstance(evidence_links, list):
            raise ValueError("evidence_links must be list[str]")
        normalized_links = []
        for idx, value in enumerate(evidence_links):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"evidence_links[{idx}] must be a non-empty string")
            normalized_links.append(value.strip())
        found["evidence_links"] = normalized_links

    if note is not None:
        note = _require_non_empty_str(note, "note")
        history = found.setdefault("comment_history", [])
        if not isinstance(history, list):
            raise ValueError("comment_history must be list")
        history.append(
            {
                "created_at": utc_now_iso(),
                "note": note,
            }
        )

    found["updated_at"] = utc_now_iso()
    state["updated_at"] = utc_now_iso()

    paths = AuditRunPaths.for_run(run_id, store_root)
    _atomic_write_json(paths.remediation_state_path, state)
    return found


def build_remediation_summary(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    items = list_remediations(run_id, store_root)
    counts: dict[str, int] = {}
    for row in items:
        status = str(row.get("status", "UNKNOWN"))
        counts[status] = counts.get(status, 0) + 1

    return {
        "run_id": run_id,
        "item_count": len(items),
        "status_counts": counts,
        "items": items,
    }
