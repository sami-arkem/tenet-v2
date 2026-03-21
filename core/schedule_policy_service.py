from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_POLICY_ROOT = Path("fixtures") / "schedules_policy"

FREQ_MANUAL = "MANUAL"
FREQ_MONTHLY = "MONTHLY"
FREQ_QUARTERLY = "QUARTERLY"
FREQ_BIANNUAL = "BIANNUAL"
FREQ_ANNUAL = "ANNUAL"
FREQ_CUSTOM = "CUSTOM"

ALLOWED_FREQUENCIES = {
    FREQ_MANUAL,
    FREQ_MONTHLY,
    FREQ_QUARTERLY,
    FREQ_BIANNUAL,
    FREQ_ANNUAL,
    FREQ_CUSTOM,
}

STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_DISABLED = "DISABLED"
ALLOWED_STATUSES = {
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_DISABLED,
}

SKIP_MANUAL_ONLY = "MANUAL_ONLY"
SKIP_INACTIVE = "INACTIVE"
SKIP_NOT_DUE = "NOT_DUE"
SKIP_STALE_EVIDENCE = "STALE_EVIDENCE"
SKIP_MISSING_EVIDENCE_TIMESTAMP = "MISSING_EVIDENCE_TIMESTAMP"

AUTO_RUN_STALE_EVIDENCE_MAX_DAYS = 60
DEFAULT_NOTIFY_BEFORE_DAYS = 7


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def utc_today() -> date:
    return utc_now().date()


def new_policy_schedule_id() -> str:
    return f"as_{uuid.uuid4().hex[:16]}"


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


def _parse_iso_date(value: str, field_name: str) -> date:
    value = _require_non_empty_str(value, field_name)
    return date.fromisoformat(value)


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    value = _require_non_empty_str(value, field_name)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone")
    return dt.astimezone(timezone.utc)


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


def _schedule_path(schedule_id: str, root: Path = DEFAULT_POLICY_ROOT) -> Path:
    schedule_id = _require_non_empty_str(schedule_id, "schedule_id")
    return root / f"{schedule_id}.json"


def _month_add(input_date: date, months: int) -> date:
    if months <= 0:
        raise ValueError("months must be positive")
    year = input_date.year + ((input_date.month - 1 + months) // 12)
    month = ((input_date.month - 1 + months) % 12) + 1
    day = min(input_date.day, 28)
    return date(year, month, day)


def _compute_next_run_date(*, frequency: str, current_next_run_date: date, custom_interval_days: int | None) -> date:
    if frequency == FREQ_MANUAL:
        return current_next_run_date
    if frequency == FREQ_MONTHLY:
        return _month_add(current_next_run_date, 1)
    if frequency == FREQ_QUARTERLY:
        return _month_add(current_next_run_date, 3)
    if frequency == FREQ_BIANNUAL:
        return _month_add(current_next_run_date, 6)
    if frequency == FREQ_ANNUAL:
        return _month_add(current_next_run_date, 12)
    if frequency == FREQ_CUSTOM:
        if not isinstance(custom_interval_days, int) or custom_interval_days <= 0:
            raise ValueError("custom_interval_days must be positive int for CUSTOM schedules")
        return current_next_run_date + timedelta(days=custom_interval_days)
    raise ValueError(f"unsupported frequency: {frequency}")


def _extract_latest_evidence_at(audit_payload: dict[str, Any]) -> datetime | None:
    audit_payload = _require_dict(audit_payload, "audit_payload")
    candidates = [
        audit_payload.get("latest_evidence_at"),
        (audit_payload.get("evidence_summary") or {}).get("latest_evidence_at")
        if isinstance(audit_payload.get("evidence_summary"), dict)
        else None,
        (audit_payload.get("corpus") or {}).get("latest_evidence_at")
        if isinstance(audit_payload.get("corpus"), dict)
        else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return _parse_iso_datetime(value, "audit_payload.latest_evidence_at")
    return None


def _normalize_schedule_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _require_dict(payload, "schedule")

    schedule_id = payload.get("schedule_id")
    if schedule_id is None:
        schedule_id = new_policy_schedule_id()
    schedule_id = _require_non_empty_str(schedule_id, "schedule.schedule_id")

    tenant_id = _require_non_empty_str(payload.get("tenant_id"), "schedule.tenant_id")
    created_by = _require_non_empty_str(payload.get("created_by"), "schedule.created_by")
    name = _require_non_empty_str(payload.get("name"), "schedule.name")
    jurisdiction = _require_non_empty_str(payload.get("jurisdiction"), "schedule.jurisdiction")
    frequency = _require_non_empty_str(payload.get("frequency"), "schedule.frequency").upper()
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError(f"frequency must be one of {sorted(ALLOWED_FREQUENCIES)}")

    regime_scope = [str(x).strip() for x in _require_list(payload.get("regime_scope"), "schedule.regime_scope") if str(x).strip()]
    if not regime_scope:
        raise ValueError("schedule.regime_scope must be non-empty")

    next_run_date = _parse_iso_date(payload.get("next_run_date"), "schedule.next_run_date")
    notify_before_days = payload.get("notify_before_days", DEFAULT_NOTIFY_BEFORE_DAYS)
    if not isinstance(notify_before_days, int) or notify_before_days < 0:
        raise ValueError("notify_before_days must be non-negative int")

    notify_users = [str(x).strip() for x in _require_list(payload.get("notify_users", []), "schedule.notify_users") if str(x).strip()]
    status = _require_non_empty_str(payload.get("status", STATUS_ACTIVE), "schedule.status").upper()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUSES)}")

    is_active = payload.get("is_active")
    if is_active is None:
        is_active = status == STATUS_ACTIVE
    if not isinstance(is_active, bool):
        raise ValueError("is_active must be bool")

    entity_id = payload.get("entity_id")
    if entity_id is not None:
        entity_id = _require_non_empty_str(entity_id, "schedule.entity_id")

    custom_interval_days = payload.get("custom_interval_days")
    if frequency == FREQ_CUSTOM:
        if not isinstance(custom_interval_days, int) or custom_interval_days <= 0:
            raise ValueError("custom_interval_days must be positive int for CUSTOM frequency")
    else:
        if custom_interval_days is not None:
            raise ValueError("custom_interval_days only valid for CUSTOM frequency")

    audit_payload = _require_dict(payload.get("audit_payload"), "schedule.audit_payload")
    last_run_id = payload.get("last_run_id")
    if last_run_id is not None:
        last_run_id = _require_non_empty_str(last_run_id, "schedule.last_run_id")

    last_run_at = payload.get("last_run_at")
    if last_run_at is not None:
        _parse_iso_datetime(last_run_at, "schedule.last_run_at")

    created_at = payload.get("created_at") or utc_now_iso()
    updated_at = payload.get("updated_at") or utc_now_iso()

    return {
        "schedule_id": schedule_id,
        "tenant_id": tenant_id,
        "entity_id": entity_id,
        "created_by": created_by,
        "name": name,
        "regime_scope": regime_scope,
        "jurisdiction": jurisdiction,
        "frequency": frequency,
        "custom_interval_days": custom_interval_days,
        "next_run_date": next_run_date.isoformat(),
        "last_run_id": last_run_id,
        "last_run_at": last_run_at,
        "notify_before_days": notify_before_days,
        "notify_users": notify_users,
        "status": status,
        "is_active": is_active,
        "audit_payload": audit_payload,
        "created_at": created_at,
        "updated_at": updated_at,
        "deterministic_authoritative": True,
    }


def create_policy_schedule(
    *,
    tenant_id: str,
    created_by: str,
    name: str,
    regime_scope: list[str],
    jurisdiction: str,
    frequency: str,
    next_run_date: str,
    audit_payload: dict[str, Any],
    entity_id: str | None = None,
    notify_before_days: int = DEFAULT_NOTIFY_BEFORE_DAYS,
    notify_users: list[str] | None = None,
    custom_interval_days: int | None = None,
    root: Path = DEFAULT_POLICY_ROOT,
) -> dict[str, Any]:
    payload = _normalize_schedule_payload(
        {
            "tenant_id": tenant_id,
            "created_by": created_by,
            "name": name,
            "regime_scope": regime_scope,
            "jurisdiction": jurisdiction,
            "frequency": frequency,
            "next_run_date": next_run_date,
            "audit_payload": audit_payload,
            "entity_id": entity_id,
            "notify_before_days": notify_before_days,
            "notify_users": notify_users or [],
            "custom_interval_days": custom_interval_days,
            "status": STATUS_ACTIVE,
            "is_active": True,
        }
    )
    _atomic_write_json(_schedule_path(payload["schedule_id"], root), payload)
    return payload


def get_policy_schedule(*, schedule_id: str, root: Path = DEFAULT_POLICY_ROOT) -> dict[str, Any]:
    path = _schedule_path(schedule_id, root)
    if not path.exists():
        raise FileNotFoundError(f"schedule not found: {schedule_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("schedule must be object")
    return payload


def list_policy_schedules(root: Path = DEFAULT_POLICY_ROOT) -> dict[str, Any]:
    if not root.exists():
        return {"count": 0, "items": [], "deterministic_authoritative": True}

    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("as_*.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)

    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows,
        "deterministic_authoritative": True,
    }


def update_policy_schedule(*, schedule_id: str, root: Path = DEFAULT_POLICY_ROOT, **changes: Any) -> dict[str, Any]:
    current = get_policy_schedule(schedule_id=schedule_id, root=root)
    merged = {**current, **changes, "schedule_id": schedule_id, "updated_at": utc_now_iso()}
    normalized = _normalize_schedule_payload(merged)
    _atomic_write_json(_schedule_path(schedule_id, root), normalized)
    return normalized


def delete_policy_schedule(*, schedule_id: str, root: Path = DEFAULT_POLICY_ROOT) -> dict[str, Any]:
    path = _schedule_path(schedule_id, root)
    if not path.exists():
        raise FileNotFoundError(f"schedule not found: {schedule_id}")
    previous = _load_json(path)
    path.unlink()
    return {
        "schedule_id": schedule_id,
        "deleted": True,
        "previous": previous,
        "deterministic_authoritative": True,
    }


def build_schedule_reminder_plan(*, as_of_date: date | None = None, root: Path = DEFAULT_POLICY_ROOT) -> dict[str, Any]:
    as_of_date = as_of_date or utc_today()
    schedules = list_policy_schedules(root=root)["items"]

    items: list[dict[str, Any]] = []
    for schedule in schedules:
        if not isinstance(schedule, dict):
            continue
        if schedule.get("status") != STATUS_ACTIVE or schedule.get("is_active") is not True:
            continue
        if schedule.get("frequency") == FREQ_MANUAL:
            continue

        next_run_date = _parse_iso_date(schedule["next_run_date"], "next_run_date")
        notify_before_days = int(schedule["notify_before_days"])
        reminder_date = next_run_date - timedelta(days=notify_before_days)
        if reminder_date != as_of_date:
            continue

        items.append(
            {
                "schedule_id": schedule["schedule_id"],
                "tenant_id": schedule["tenant_id"],
                "notify_users": schedule["notify_users"],
                "reminder_date": reminder_date.isoformat(),
                "next_run_date": next_run_date.isoformat(),
                "notify_before_days": notify_before_days,
                "message": (
                    f"Your {str(schedule['frequency']).lower()} audit is due in "
                    f"{notify_before_days} days. We will auto-run on {next_run_date.isoformat()}. "
                    "Upload updated evidence before then."
                ),
            }
        )

    return {
        "as_of_date": as_of_date.isoformat(),
        "count": len(items),
        "items": items,
        "deterministic_authoritative": True,
    }


def evaluate_schedule_auto_run_eligibility(*, schedule: dict[str, Any], as_of_date: date | None = None) -> dict[str, Any]:
    schedule = _require_dict(schedule, "schedule")
    as_of_date = as_of_date or utc_today()

    frequency = _require_non_empty_str(schedule.get("frequency"), "schedule.frequency")
    status = _require_non_empty_str(schedule.get("status"), "schedule.status")
    is_active = bool(schedule.get("is_active"))
    next_run_date = _parse_iso_date(schedule.get("next_run_date"), "schedule.next_run_date")

    skip_reasons: list[str] = []
    if status != STATUS_ACTIVE or is_active is not True:
        skip_reasons.append(SKIP_INACTIVE)
    if frequency == FREQ_MANUAL:
        skip_reasons.append(SKIP_MANUAL_ONLY)
    if next_run_date > as_of_date:
        skip_reasons.append(SKIP_NOT_DUE)

    latest_evidence_at = _extract_latest_evidence_at(schedule.get("audit_payload", {}))
    evidence_age_days = None
    if latest_evidence_at is None:
        skip_reasons.append(SKIP_MISSING_EVIDENCE_TIMESTAMP)
    else:
        evidence_age_days = (as_of_date - latest_evidence_at.date()).days
        if evidence_age_days > AUTO_RUN_STALE_EVIDENCE_MAX_DAYS:
            skip_reasons.append(SKIP_STALE_EVIDENCE)

    return {
        "schedule_id": schedule["schedule_id"],
        "eligible": len(skip_reasons) == 0,
        "skip_reasons": skip_reasons,
        "next_run_date": next_run_date.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "latest_evidence_at": latest_evidence_at.isoformat() if latest_evidence_at else None,
        "evidence_age_days": evidence_age_days,
        "deterministic_authoritative": True,
    }


def build_due_execution_plan(*, as_of_date: date | None = None, limit: int = 50, root: Path = DEFAULT_POLICY_ROOT) -> dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be positive int")
    as_of_date = as_of_date or utc_today()

    schedules = list_policy_schedules(root=root)["items"]
    eligible_items: list[dict[str, Any]] = []
    skipped_items: list[dict[str, Any]] = []

    for schedule in schedules:
        if not isinstance(schedule, dict):
            continue
        eligibility = evaluate_schedule_auto_run_eligibility(schedule=schedule, as_of_date=as_of_date)
        if eligibility["eligible"] is True:
            eligible_items.append(
                {
                    "schedule_id": schedule["schedule_id"],
                    "tenant_id": schedule["tenant_id"],
                    "entity_id": schedule.get("entity_id"),
                    "name": schedule["name"],
                    "regime_scope": schedule["regime_scope"],
                    "jurisdiction": schedule["jurisdiction"],
                    "scheduled_for": schedule["next_run_date"],
                    "audit_run_request": {
                        "trigger_type": "SCHEDULED_AUTO_RUN",
                        "schedule_id": schedule["schedule_id"],
                        "tenant_id": schedule["tenant_id"],
                        "entity_id": schedule.get("entity_id"),
                        "regime_scope": schedule["regime_scope"],
                        "jurisdiction": schedule["jurisdiction"],
                        "audit_payload": schedule["audit_payload"],
                    },
                }
            )
        else:
            skipped_items.append(
                {
                    "schedule_id": schedule["schedule_id"],
                    "tenant_id": schedule["tenant_id"],
                    "scheduled_for": schedule["next_run_date"],
                    "skip_reasons": eligibility["skip_reasons"],
                }
            )

    eligible_items.sort(key=lambda row: (row["scheduled_for"], row["schedule_id"]))
    skipped_items.sort(key=lambda row: (row["scheduled_for"], row["schedule_id"]))
    return {
        "as_of_date": as_of_date.isoformat(),
        "eligible_count": len(eligible_items),
        "scheduled_count": min(limit, len(eligible_items)),
        "eligible_items": eligible_items[:limit],
        "skipped_count": len(skipped_items),
        "skipped_items": skipped_items,
        "deterministic_authoritative": True,
    }


def mark_policy_schedule_executed(
    *,
    schedule_id: str,
    last_run_id: str,
    executed_at: str,
    root: Path = DEFAULT_POLICY_ROOT,
) -> dict[str, Any]:
    schedule = get_policy_schedule(schedule_id=schedule_id, root=root)
    executed_dt = _parse_iso_datetime(executed_at, "executed_at")
    current_next_run_date = _parse_iso_date(schedule["next_run_date"], "next_run_date")

    next_run_date = _compute_next_run_date(
        frequency=schedule["frequency"],
        current_next_run_date=current_next_run_date,
        custom_interval_days=schedule.get("custom_interval_days"),
    )

    updated = {
        **schedule,
        "last_run_id": _require_non_empty_str(last_run_id, "last_run_id"),
        "last_run_at": executed_dt.isoformat(),
        "next_run_date": next_run_date.isoformat(),
        "updated_at": utc_now_iso(),
    }
    normalized = _normalize_schedule_payload(updated)
    _atomic_write_json(_schedule_path(schedule_id, root), normalized)
    return normalized
