from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.dataset_registry_service import DEFAULT_DATASET_ROOT, load_dataset_registry


DEFAULT_FRESHNESS_ROOT = Path("fixtures") / "regulatory_datasets" / "_freshness"

CADENCE_TO_MAX_AGE_DAYS = {
    "DAILY": 2,
    "WEEKLY": 8,
    "MONTHLY": 35,
    "QUARTERLY": 100,
    "AD_HOC": 180,
    "STATIC": 3650,
}

CADENCE_TO_REFRESH_INTERVAL_DAYS = {
    "DAILY": 1,
    "WEEKLY": 7,
    "MONTHLY": 30,
    "QUARTERLY": 90,
    "AD_HOC": 90,
    "STATIC": 365,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


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


def _freshness_status_path(dataset_id: str, root: Path = DEFAULT_FRESHNESS_ROOT) -> Path:
    dataset_id = _require_non_empty_str(dataset_id, "dataset_id")
    return root / f"{dataset_id}.json"


def _parse_iso_date(value: str | None) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return date.fromisoformat(value.strip())


def _parse_iso_datetime_to_date(value: str | None) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).date()


def _extract_last_refresh_date(item: dict[str, Any]) -> date | None:
    ingested_at = item.get("last_ingested_at")
    if isinstance(ingested_at, str) and ingested_at.strip():
        try:
            return _parse_iso_datetime_to_date(ingested_at)
        except Exception:
            pass
    return _parse_iso_date(item.get("freshness_date"))


def _compute_freshness_status(item: dict[str, Any]) -> dict[str, Any]:
    dataset_id = _require_non_empty_str(item.get("dataset_id"), "dataset.dataset_id")
    title = _require_non_empty_str(item.get("title"), "dataset.title")
    update_cadence = _require_non_empty_str(item.get("update_cadence"), "dataset.update_cadence")
    status = _require_non_empty_str(item.get("status"), "dataset.status")
    retrieval_ready = bool(item.get("retrieval_ready"))

    max_age_days = CADENCE_TO_MAX_AGE_DAYS.get(update_cadence)
    if max_age_days is None:
        raise ValueError(f"unsupported update cadence: {update_cadence}")

    refresh_interval_days = CADENCE_TO_REFRESH_INTERVAL_DAYS[update_cadence]
    today = utc_today()
    last_refresh_date = _extract_last_refresh_date(item)

    if last_refresh_date is None:
        age_days = None
        freshness_state = "UNKNOWN"
        next_refresh_date = today.isoformat()
        refresh_due = True
    else:
        age_days = (today - last_refresh_date).days
        if age_days <= max_age_days:
            freshness_state = "FRESH"
        elif age_days <= max_age_days * 2:
            freshness_state = "STALE"
        else:
            freshness_state = "EXPIRED"
        next_refresh_date = (last_refresh_date + timedelta(days=refresh_interval_days)).isoformat()
        refresh_due = today >= (last_refresh_date + timedelta(days=refresh_interval_days))

    refresh_allowed = (
        status == "ACTIVE"
        and retrieval_ready is True
        and freshness_state in {"STALE", "EXPIRED", "UNKNOWN"}
    )

    priority = "LOW"
    if freshness_state == "EXPIRED":
        priority = "HIGH"
    elif freshness_state in {"STALE", "UNKNOWN"}:
        priority = "MEDIUM"

    return {
        "dataset_id": dataset_id,
        "title": title,
        "domain": item.get("domain"),
        "jurisdictions": item.get("jurisdictions", []),
        "countries": item.get("countries", []),
        "framework_ids": item.get("framework_ids", []),
        "dataset_type": item.get("dataset_type"),
        "license_type": item.get("license_type"),
        "status": status,
        "update_cadence": update_cadence,
        "retrieval_ready": retrieval_ready,
        "last_refresh_date": last_refresh_date.isoformat() if last_refresh_date else None,
        "age_days": age_days,
        "freshness_state": freshness_state,
        "next_refresh_date": next_refresh_date,
        "refresh_due": refresh_due,
        "refresh_allowed": refresh_allowed,
        "priority": priority,
        "deterministic_authoritative": True,
        "evaluated_at": utc_now_iso(),
    }


def build_dataset_freshness_registry(
    *,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    freshness_root: Path = DEFAULT_FRESHNESS_ROOT,
) -> dict[str, Any]:
    registry = load_dataset_registry(dataset_root)
    rows: list[dict[str, Any]] = []

    for item in registry["items"]:
        if not isinstance(item, dict):
            continue
        row = _compute_freshness_status(item)
        rows.append(row)
        _atomic_write_json(_freshness_status_path(row["dataset_id"], freshness_root), row)

    fresh = sum(1 for row in rows if row["freshness_state"] == "FRESH")
    stale = sum(1 for row in rows if row["freshness_state"] == "STALE")
    expired = sum(1 for row in rows if row["freshness_state"] == "EXPIRED")
    unknown = sum(1 for row in rows if row["freshness_state"] == "UNKNOWN")
    refresh_due_count = sum(1 for row in rows if row["refresh_due"] is True)

    return {
        "deterministic_authoritative": True,
        "dataset_count": len(rows),
        "fresh": fresh,
        "stale": stale,
        "expired": expired,
        "unknown": unknown,
        "refresh_due_count": refresh_due_count,
        "items": rows,
        "generated_at": utc_now_iso(),
    }


def get_dataset_freshness_status(
    *,
    dataset_id: str,
    freshness_root: Path = DEFAULT_FRESHNESS_ROOT,
) -> dict[str, Any]:
    path = _freshness_status_path(dataset_id, freshness_root)
    if not path.exists():
        raise FileNotFoundError(f"dataset freshness status not found: {dataset_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("dataset freshness status must be object")
    return payload


def build_refresh_plan(
    *,
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    freshness_root: Path = DEFAULT_FRESHNESS_ROOT,
    limit: int = 50,
) -> dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be positive int")

    registry = build_dataset_freshness_registry(
        dataset_root=dataset_root,
        freshness_root=freshness_root,
    )
    candidates = [row for row in registry["items"] if row["refresh_allowed"] is True]
    candidates.sort(
        key=lambda row: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(str(row.get("priority")), 9),
            -(row["age_days"] if isinstance(row.get("age_days"), int) else -1),
            str(row.get("dataset_id")),
        )
    )

    return {
        "deterministic_authoritative": True,
        "candidate_count": len(candidates),
        "scheduled_count": min(limit, len(candidates)),
        "items": candidates[:limit],
        "generated_at": utc_now_iso(),
    }
