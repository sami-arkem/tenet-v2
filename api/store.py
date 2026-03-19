from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.audit_pipeline import build_execution_bundle, result_to_snapshot, run_audit_from_payload
from core.export_package import export_audit_package
from core.report_renderer import render_report_bundle
from core.remediation_service import reseed_remediation_state
from core.review_service import reset_review_state


DEFAULT_STORE_ROOT = Path("artifacts") / "audit_runs"
DEFAULT_EXPORT_ROOT = Path("artifacts") / "audit_packages"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_relative_dir(value: str | None, default: Path) -> Path:
    if value is None:
        return default
    path = Path(value)
    if path.is_absolute():
        raise ValueError("path must be relative")
    if ".." in path.parts:
        raise ValueError("path must not contain parent traversal")
    return path


@dataclass(frozen=True)
class StoredAuditPaths:
    root: Path
    payload_path: Path
    detail_path: Path

    @staticmethod
    def for_run(run_id: str, store_root: Path) -> "StoredAuditPaths":
        root = store_root / run_id
        return StoredAuditPaths(
            root=root,
            payload_path=root / "input_payload.json",
            detail_path=root / "detail.json",
        )


def execute_and_store_audit(
    *,
    payload: dict[str, Any],
    export: dict[str, Any] | None = None,
    store_root: Path = DEFAULT_STORE_ROOT,
) -> dict[str, Any]:
    result = run_audit_from_payload(payload)
    execution_bundle = build_execution_bundle(payload)
    report_bundle = render_report_bundle(result)
    snapshot = result_to_snapshot(result)

    export_package = None
    if export and bool(export.get("create_export_package")):
        export_root = resolve_relative_dir(export.get("export_root"), DEFAULT_EXPORT_ROOT)
        export_package = export_audit_package(
            payload=payload,
            export_root=export_root,
            package_name=export.get("package_name"),
            package_version=str(export.get("package_version", "v1")),
        )

    paths = StoredAuditPaths.for_run(result.run_id, store_root)
    paths.root.mkdir(parents=True, exist_ok=True)

    atomic_write_json(paths.payload_path, payload)
    detail = {
        "run_id": result.run_id,
        "created_at": utc_now_iso(),
        "input_payload": payload,
        "deterministic_audit_result": execution_bundle["deterministic_audit_result"],
        "report_pack": execution_bundle["report_pack"],
        "report_bundle": report_bundle,
        "snapshot": snapshot,
        "topline": execution_bundle["topline"],
        "export_package": export_package,
        "audit_context_pack": payload.get("audit_context_pack"),
    }
    atomic_write_json(paths.detail_path, detail)
    reset_review_state(result.run_id, store_root)
    reseed_remediation_state(result.run_id, store_root)
    return detail


def get_audit_detail(run_id: str, store_root: Path = DEFAULT_STORE_ROOT) -> dict[str, Any]:
    path = StoredAuditPaths.for_run(run_id, store_root).detail_path
    if not path.exists():
        raise FileNotFoundError(f"audit run not found: {run_id}")
    return load_json(path)


def list_audits(store_root: Path = DEFAULT_STORE_ROOT) -> list[dict[str, Any]]:
    if not store_root.exists():
        return []

    items: list[dict[str, Any]] = []
    for run_dir in sorted([path for path in store_root.iterdir() if path.is_dir()]):
        detail_path = run_dir / "detail.json"
        if not detail_path.exists():
            continue
        try:
            detail = load_json(detail_path)
        except Exception:
            continue

        deterministic = detail.get("deterministic_audit_result", {})
        company = deterministic.get("company_profile", {})
        scope = deterministic.get("scope", {})
        summary = deterministic.get("summary", {})

        items.append(
            {
                "run_id": detail.get("run_id"),
                "company_name": company.get("company_name"),
                "audit_type": scope.get("audit_type"),
                "overall_posture": summary.get("overall_posture"),
                "deployment_decision": summary.get("deployment_decision"),
                "created_at": detail.get("created_at"),
            }
        )

    items.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return items
