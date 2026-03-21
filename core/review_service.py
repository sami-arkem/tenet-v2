from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_STORE_ROOT = Path("artifacts") / "audit_runs"


ALLOWED_REVIEW_DECISIONS = {
    "APPROVED",
    "CONDITIONALLY_APPROVED",
    "REJECTED",
}

ALLOWED_REVIEW_STATUSES = {
    "PENDING_REVIEW",
    "REVIEWED",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_list_of_strings(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list[str]")
    out: list[str] = []
    for idx, row in enumerate(value):
        if not isinstance(row, str) or not row.strip():
            raise ValueError(f"{field_name}[{idx}] must be a non-empty string")
        out.append(row.strip())
    return out


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


def _detail_path(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> Path:
    run_id = _require_non_empty_str(run_id, "run_id")
    return store_root / run_id / "detail.json"


def _review_state_path(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> Path:
    run_id = _require_non_empty_str(run_id, "run_id")
    return store_root / run_id / "review_state.json"


def _load_audit_detail(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    path = _detail_path(run_id, store_root)
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    detail = _load_json(path)
    if not isinstance(detail, dict):
        raise ValueError("audit detail must be an object")
    return detail


def _seed_review_state(detail: dict[str, Any]) -> dict[str, Any]:
    run_id = _require_non_empty_str(detail.get("run_id"), "detail.run_id")
    deterministic = detail.get("deterministic_audit_result", {})
    export_package = detail.get("export_package")

    summary = deterministic.get("summary", {})
    scope = deterministic.get("scope", {})
    company = deterministic.get("company_profile", {})

    now = utc_now_iso()
    return {
        "run_id": run_id,
        "created_at": now,
        "updated_at": now,
        "status": "PENDING_REVIEW",
        "baseline": {
            "company_name": company.get("company_name"),
            "audit_type": scope.get("audit_type"),
            "overall_posture": summary.get("overall_posture"),
            "deployment_decision": summary.get("deployment_decision"),
            "finding_count": len(deterministic.get("findings", [])),
            "remediation_item_count": len(deterministic.get("remediation_items", [])),
        },
        "export_package": {
            "present": export_package is not None,
            "package_paths": export_package.get("package_paths") if isinstance(export_package, dict) else None,
            "manifest": export_package.get("manifest") if isinstance(export_package, dict) else None,
            "verification": export_package.get("verification") if isinstance(export_package, dict) else None,
        },
        "latest_review": None,
        "review_history": [],
    }


def ensure_review_state(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    state_path = _review_state_path(run_id, store_root)
    if state_path.exists():
        state = _load_json(state_path)
        if not isinstance(state, dict):
            raise ValueError("review state must be an object")
        return state

    detail = _load_audit_detail(run_id, store_root)
    state = _seed_review_state(detail)
    _atomic_write_json(state_path, state)
    return state


def get_review_state(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    return ensure_review_state(run_id, store_root)


def reset_review_state(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> None:
    path = _review_state_path(run_id, store_root)
    if path.exists():
        path.unlink()


def submit_review_decision(
    *,
    run_id: str,
    reviewer: str,
    decision: str,
    rationale: str,
    conditions: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    note: str | None = None,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    reviewer = _require_non_empty_str(reviewer, "reviewer")
    decision = _require_non_empty_str(decision, "decision").upper()
    rationale = _require_non_empty_str(rationale, "rationale")

    if decision not in ALLOWED_REVIEW_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(ALLOWED_REVIEW_DECISIONS)}")

    normalized_conditions = _require_list_of_strings(conditions or [], "conditions")
    normalized_evidence_refs = _require_list_of_strings(evidence_refs or [], "evidence_refs")

    if decision == "CONDITIONALLY_APPROVED" and not normalized_conditions:
        raise ValueError("conditions are required for CONDITIONALLY_APPROVED")
    if decision == "REJECTED" and not normalized_conditions:
        raise ValueError("conditions are required for REJECTED")

    state = ensure_review_state(run_id, store_root)
    now = utc_now_iso()

    review_record = {
        "reviewed_at": now,
        "reviewer": reviewer,
        "decision": decision,
        "rationale": rationale,
        "conditions": normalized_conditions,
        "evidence_refs": normalized_evidence_refs,
        "note": _require_non_empty_str(note, "note") if note is not None else None,
    }

    state["latest_review"] = review_record
    state["review_history"].append(deepcopy(review_record))
    state["status"] = "REVIEWED"
    state["updated_at"] = now

    if state["status"] not in ALLOWED_REVIEW_STATUSES:
        raise ValueError("invalid review status")

    state_path = _review_state_path(run_id, store_root)
    _atomic_write_json(state_path, state)
    return state


def build_review_summary(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    state = ensure_review_state(run_id, store_root)
    latest_review = state.get("latest_review")
    review_history = state.get("review_history", [])

    approved = latest_review["decision"] == "APPROVED" if isinstance(latest_review, dict) else False
    conditionally_approved = latest_review["decision"] == "CONDITIONALLY_APPROVED" if isinstance(latest_review, dict) else False
    rejected = latest_review["decision"] == "REJECTED" if isinstance(latest_review, dict) else False

    return {
        "run_id": state["run_id"],
        "status": state["status"],
        "baseline": state["baseline"],
        "export_package": state["export_package"],
        "latest_review": latest_review,
        "review_count": len(review_history) if isinstance(review_history, list) else 0,
        "approved": approved,
        "conditionally_approved": conditionally_approved,
        "rejected": rejected,
        "review_history": review_history,
        "created_at": state["created_at"],
        "updated_at": state["updated_at"],
    }
