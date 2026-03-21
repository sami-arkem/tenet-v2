from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.evidence_pack_service import DEFAULT_PACK_ROOT, execute_evidence_pack, get_evidence_pack
from core.readiness_service import build_readiness_plan
from core.remediation_service import DEFAULT_STORE_ROOT, build_remediation_summary


DEFAULT_WORKFLOW_ROOT = Path("artifacts") / "workflow_runs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_workflow_id() -> str:
    return f"wf_{uuid.uuid4().hex[:16]}"


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


class WorkflowStateError(RuntimeError):
    pass


def workflow_paths(workflow_id: str, workflow_root: Path = DEFAULT_WORKFLOW_ROOT) -> dict[str, Path]:
    workflow_id = _require_non_empty_str(workflow_id, "workflow_id")
    root = workflow_root / workflow_id
    return {
        "root": root,
        "detail": root / "detail.json",
    }


def _append_event(detail: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
    detail.setdefault("timeline", [])
    detail["timeline"].append(
        {
            "created_at": utc_now_iso(),
            "event_type": event_type,
            "payload": payload,
        }
    )
    detail["updated_at"] = utc_now_iso()


def create_workflow(
    *,
    pack_id: str,
    created_by: str,
    workflow_root: Path = DEFAULT_WORKFLOW_ROOT,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    pack_id = _require_non_empty_str(pack_id, "pack_id")
    created_by = _require_non_empty_str(created_by, "created_by")

    pack = get_evidence_pack(pack_id, pack_root=pack_root)
    pack_detail = pack["detail"]

    workflow_id = new_workflow_id()
    paths = workflow_paths(workflow_id, workflow_root)

    state = {
        "workflow_id": workflow_id,
        "pack_id": pack_id,
        "pack_name": pack_detail["name"],
        "company_name": pack_detail["manifest_summary"]["company_name"],
        "audit_type": pack_detail["manifest_summary"]["audit_type"],
        "domain": pack_detail["manifest_summary"]["domain"],
        "jurisdictions": pack_detail["manifest_summary"]["jurisdictions"],
        "created_by": created_by,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "status": "CREATED",
        "latest_readiness": None,
        "latest_execution": None,
        "latest_remediation_summary": None,
        "timeline": [],
    }
    _append_event(
        state,
        "workflow_created",
        {
            "pack_id": pack_id,
            "pack_name": pack_detail["name"],
            "created_by": created_by,
        },
    )

    paths["root"].mkdir(parents=True, exist_ok=True)
    _atomic_write_json(paths["detail"], state)
    return state


def get_workflow(workflow_id: str, workflow_root: Path = DEFAULT_WORKFLOW_ROOT) -> dict[str, Any]:
    paths = workflow_paths(workflow_id, workflow_root)
    if not paths["detail"].exists():
        raise FileNotFoundError(f"workflow not found: {workflow_id}")
    return _load_json(paths["detail"])


def list_workflows(workflow_root: Path = DEFAULT_WORKFLOW_ROOT) -> list[dict[str, Any]]:
    if not workflow_root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(path for path in workflow_root.iterdir() if path.is_dir()):
        detail_path = child / "detail.json"
        if not detail_path.exists():
            continue
        try:
            rows.append(_load_json(detail_path))
        except Exception:
            continue
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows


def refresh_workflow_readiness(
    workflow_id: str,
    workflow_root: Path = DEFAULT_WORKFLOW_ROOT,
    pack_root: Path = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    detail = get_workflow(workflow_id, workflow_root)
    readiness = build_readiness_plan(detail["pack_id"], pack_root=pack_root)
    detail["latest_readiness"] = readiness
    overall_status = readiness["summary"]["overall_status"]
    corpus_ready = readiness.get("corpus_readiness", {}).get("corpus_ready") is True
    executable_statuses = {"READY", "REMEDIATION_REQUIRED", "NO_APPLICABLE_CONTROLS"}
    detail["status"] = (
        "READY_FOR_EXECUTION"
        if overall_status in executable_statuses and corpus_ready
        else "BLOCKED_BY_READINESS"
    )
    _append_event(
        detail,
        "readiness_refreshed",
        {
            "overall_status": readiness["summary"]["overall_status"],
            "corpus_ready": corpus_ready,
            "control_count": readiness["summary"]["control_count"],
            "requested_evidence_actions": len(readiness["requested_evidence_actions"]),
        },
    )
    _atomic_write_json(workflow_paths(workflow_id, workflow_root)["detail"], detail)
    return detail


def execute_workflow_audit(
    *,
    workflow_id: str,
    run_id: str,
    default_remediation_owner: str,
    export: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    workflow_root: Path = DEFAULT_WORKFLOW_ROOT,
    pack_root: Path = DEFAULT_PACK_ROOT,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    workflow_id = _require_non_empty_str(workflow_id, "workflow_id")
    run_id = _require_non_empty_str(run_id, "run_id")
    default_remediation_owner = _require_non_empty_str(default_remediation_owner, "default_remediation_owner")

    detail = get_workflow(workflow_id, workflow_root)

    if detail.get("latest_readiness") is None:
        detail = refresh_workflow_readiness(workflow_id, workflow_root, pack_root)

    readiness = detail["latest_readiness"]
    if detail.get("status") != "READY_FOR_EXECUTION":
        raise WorkflowStateError("workflow cannot execute because readiness status is NOT_READY")

    execution = execute_evidence_pack(
        pack_id=detail["pack_id"],
        run_id=run_id,
        default_remediation_owner=default_remediation_owner,
        metadata={**(metadata or {}), "workflow_id": workflow_id},
        export=export,
        pack_root=pack_root,
        store_root=store_root,
    )

    detail["latest_execution"] = execution["execution"]
    detail["status"] = "AUDIT_EXECUTED"
    _append_event(
        detail,
        "audit_executed",
        {
            "run_id": execution["execution"]["run_id"],
            "deployment_decision": execution["execution"]["topline"]["deployment_decision"],
            "overall_posture": execution["execution"]["topline"]["overall_posture"],
            "finding_count": execution["execution"]["topline"]["finding_count"],
        },
    )
    _atomic_write_json(workflow_paths(workflow_id, workflow_root)["detail"], detail)
    return detail


def refresh_workflow_remediation(
    workflow_id: str,
    workflow_root: Path = DEFAULT_WORKFLOW_ROOT,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    detail = get_workflow(workflow_id, workflow_root)
    latest_execution = detail.get("latest_execution")
    if not isinstance(latest_execution, dict) or not latest_execution.get("run_id"):
        raise WorkflowStateError("workflow has no executed audit to build remediation summary from")

    remediation_summary = build_remediation_summary(latest_execution["run_id"], store_root=store_root)
    detail["latest_remediation_summary"] = remediation_summary
    detail["status"] = "REMEDIATION_ACTIVE" if remediation_summary["item_count"] > 0 else "COMPLETED_NO_REMEDIATION"
    _append_event(
        detail,
        "remediation_refreshed",
        {
            "run_id": latest_execution["run_id"],
            "item_count": remediation_summary["item_count"],
            "status_counts": remediation_summary["status_counts"],
        },
    )
    _atomic_write_json(workflow_paths(workflow_id, workflow_root)["detail"], detail)
    return detail


def build_workflow_summary(workflow_id: str, workflow_root: Path = DEFAULT_WORKFLOW_ROOT) -> dict[str, Any]:
    detail = get_workflow(workflow_id, workflow_root)
    return {
        "workflow_id": detail["workflow_id"],
        "pack_id": detail["pack_id"],
        "pack_name": detail["pack_name"],
        "company_name": detail["company_name"],
        "audit_type": detail["audit_type"],
        "domain": detail["domain"],
        "jurisdictions": detail["jurisdictions"],
        "status": detail["status"],
        "latest_readiness": detail.get("latest_readiness"),
        "latest_execution": detail.get("latest_execution"),
        "latest_remediation_summary": detail.get("latest_remediation_summary"),
        "timeline": detail.get("timeline", []),
        "created_at": detail["created_at"],
        "updated_at": detail["updated_at"],
    }
