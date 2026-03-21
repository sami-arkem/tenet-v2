from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_freshness_service import DEFAULT_FRESHNESS_ROOT, build_refresh_plan
from core.dataset_ingestion_service import ingest_dataset
from core.real_dataset_run_service import fetch_real_source_to_dataset


DEFAULT_DATASET_ROOT = Path("fixtures") / "regulatory_datasets"
DEFAULT_REFRESH_RUN_ROOT = DEFAULT_DATASET_ROOT / "_refresh_runs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_refresh_run_id() -> str:
    return f"refresh_{uuid.uuid4().hex[:16]}"


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


def _run_dir(run_id: str, root: Path = DEFAULT_REFRESH_RUN_ROOT) -> Path:
    run_id = _require_non_empty_str(run_id, "run_id")
    return root / run_id


def _run_status_path(run_id: str, root: Path = DEFAULT_REFRESH_RUN_ROOT) -> Path:
    return _run_dir(run_id, root) / "status.json"


def _run_items_path(run_id: str, root: Path = DEFAULT_REFRESH_RUN_ROOT) -> Path:
    return _run_dir(run_id, root) / "items.json"


def _append_item(rows: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("item payload must be object")
    rows.append(payload)


def _infer_source_id_from_dataset(dataset_row: dict[str, Any]) -> str | None:
    metadata = dataset_row.get("metadata", {})
    if isinstance(metadata, dict):
        source_id = metadata.get("promoted_from_source_id")
        if isinstance(source_id, str) and source_id.strip():
            return source_id.strip()
    return None


def _execute_refresh_for_dataset(
    dataset_row: dict[str, Any],
    *,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
) -> dict[str, Any]:
    dataset_id = _require_non_empty_str(dataset_row.get("dataset_id"), "dataset.dataset_id")
    source_id = _infer_source_id_from_dataset(dataset_row)

    fetch_payload = None
    if source_id:
        fetch_payload = fetch_real_source_to_dataset(
            source_id=source_id,
            dataset_root=dataset_root,
        )

    ingest_payload = ingest_dataset(dataset_id=dataset_id, root=dataset_root)

    return {
        "dataset_id": dataset_id,
        "source_id": source_id,
        "fetch_executed": fetch_payload is not None,
        "fetch_payload": fetch_payload,
        "ingestion_payload": ingest_payload,
        "refreshed_at": utc_now_iso(),
        "deterministic_authoritative": True,
    }


def execute_dataset_refresh_run(
    *,
    limit: int = 25,
    refresh_run_root: Path = DEFAULT_REFRESH_RUN_ROOT,
) -> dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be positive int")

    freshness_root = DEFAULT_DATASET_ROOT / "_freshness"
    plan = build_refresh_plan(
        dataset_root=DEFAULT_DATASET_ROOT,
        freshness_root=freshness_root if freshness_root != DEFAULT_FRESHNESS_ROOT else DEFAULT_FRESHNESS_ROOT,
        limit=limit,
    )
    run_id = new_refresh_run_id()

    status_payload = {
        "run_id": run_id,
        "status": "RUNNING",
        "deterministic_authoritative": True,
        "started_at": utc_now_iso(),
        "requested_limit": limit,
        "candidate_count": plan["candidate_count"],
        "scheduled_count": plan["scheduled_count"],
    }
    _atomic_write_json(_run_status_path(run_id, refresh_run_root), status_payload)

    items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for row in plan["items"]:
        if not isinstance(row, dict):
            continue
        dataset_id = row.get("dataset_id")
        try:
            result = _execute_refresh_for_dataset(
                row,
                dataset_root=DEFAULT_DATASET_ROOT,
            )
            _append_item(items, result)
        except Exception as exc:
            failures.append(
                {
                    "dataset_id": dataset_id,
                    "error": str(exc),
                    "failed_at": utc_now_iso(),
                }
            )

    final_status = {
        **status_payload,
        "status": "SUCCEEDED" if not failures else "PARTIAL_FAILURE",
        "finished_at": utc_now_iso(),
        "success_count": len(items),
        "failure_count": len(failures),
    }
    _atomic_write_json(_run_status_path(run_id, refresh_run_root), final_status)
    _atomic_write_json(
        _run_items_path(run_id, refresh_run_root),
        {
            "run_id": run_id,
            "items": items,
            "failures": failures,
            "deterministic_authoritative": True,
        },
    )

    return {
        "run_id": run_id,
        "status": final_status["status"],
        "success_count": len(items),
        "failure_count": len(failures),
        "items": items,
        "failures": failures,
        "deterministic_authoritative": True,
    }


def get_dataset_refresh_run(
    *,
    run_id: str,
    refresh_run_root: Path = DEFAULT_REFRESH_RUN_ROOT,
) -> dict[str, Any]:
    status_path = _run_status_path(run_id, refresh_run_root)
    items_path = _run_items_path(run_id, refresh_run_root)

    if not status_path.exists():
        raise FileNotFoundError(f"dataset refresh run not found: {run_id}")

    status = _load_json(status_path)
    items = _load_json(items_path) if items_path.exists() else {
        "run_id": run_id,
        "items": [],
        "failures": [],
        "deterministic_authoritative": True,
    }

    return {
        "run_id": run_id,
        "status": status.get("status"),
        "started_at": status.get("started_at"),
        "finished_at": status.get("finished_at"),
        "requested_limit": status.get("requested_limit"),
        "candidate_count": status.get("candidate_count"),
        "scheduled_count": status.get("scheduled_count"),
        "success_count": status.get("success_count", 0),
        "failure_count": status.get("failure_count", 0),
        "items": items.get("items", []),
        "failures": items.get("failures", []),
        "deterministic_authoritative": True,
    }


def list_dataset_refresh_runs(
    *,
    refresh_run_root: Path = DEFAULT_REFRESH_RUN_ROOT,
) -> dict[str, Any]:
    if not refresh_run_root.exists():
        return {
            "count": 0,
            "items": [],
            "deterministic_authoritative": True,
        }

    rows: list[dict[str, Any]] = []
    for path in sorted(refresh_run_root.glob("refresh_*/status.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "run_id": payload.get("run_id"),
                "status": payload.get("status"),
                "started_at": payload.get("started_at"),
                "finished_at": payload.get("finished_at"),
                "success_count": payload.get("success_count", 0),
                "failure_count": payload.get("failure_count", 0),
            }
        )

    rows.sort(key=lambda row: str(row.get("started_at") or ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows,
        "deterministic_authoritative": True,
    }
