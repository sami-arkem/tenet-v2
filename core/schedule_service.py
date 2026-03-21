from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_SCHEDULE_ROOT = Path("fixtures") / "schedules"

FREQ_DAILY = "DAILY"
FREQ_WEEKLY = "WEEKLY"
FREQ_MONTHLY = "MONTHLY"
ALLOWED_FREQUENCIES = {FREQ_DAILY, FREQ_WEEKLY, FREQ_MONTHLY}

STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_DISABLED = "DISABLED"
ALLOWED_STATUSES = {STATUS_ACTIVE, STATUS_PAUSED, STATUS_DISABLED}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def new_schedule_id() -> str:
    return f"sch_{uuid.uuid4().hex[:16]}"


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


def _schedule_path(schedule_id: str, root: Path = DEFAULT_SCHEDULE_ROOT) -> Path:
    return root / f"{_require_non_empty_str(schedule_id, 'schedule_id')}.json"


def _normalize_weekdays(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    allowed = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
    out: list[str] = []
    for idx, value in enumerate(values):
        normalized = _require_non_empty_str(value, f"weekdays[{idx}]").upper()
        if normalized not in allowed:
            raise ValueError("weekdays must use MO TU WE TH FR SA SU")
        if normalized not in out:
            out.append(normalized)
    return out


def _validate_schedule_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _require_dict(payload, "schedule")

    tenant_id = _require_non_empty_str(payload.get("tenant_id"), "schedule.tenant_id")
    name = _require_non_empty_str(payload.get("name"), "schedule.name")
    frequency = _require_non_empty_str(payload.get("frequency"), "schedule.frequency").upper()
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError(f"frequency must be one of {sorted(ALLOWED_FREQUENCIES)}")

    starts_at = _parse_iso_datetime(payload.get("starts_at"), "schedule.starts_at")
    timezone_name = _require_non_empty_str(payload.get("timezone"), "schedule.timezone")
    audit_payload = _require_dict(payload.get("audit_payload"), "schedule.audit_payload")

    status = payload.get("status", STATUS_ACTIVE)
    status = _require_non_empty_str(status, "schedule.status").upper()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUSES)}")

    weekdays = _normalize_weekdays(payload.get("weekdays"))
    day_of_month = payload.get("day_of_month")
    if day_of_month is not None:
        if not isinstance(day_of_month, int) or day_of_month < 1 or day_of_month > 28:
            raise ValueError("day_of_month must be int between 1 and 28")

    if frequency == FREQ_WEEKLY and not weekdays:
        raise ValueError("weekly schedules require weekdays")
    if frequency != FREQ_WEEKLY and weekdays:
        raise ValueError("weekdays only valid for weekly schedules")
    if frequency == FREQ_MONTHLY and day_of_month is None:
        raise ValueError("monthly schedules require day_of_month")
    if frequency != FREQ_MONTHLY and day_of_month is not None:
        raise ValueError("day_of_month only valid for monthly schedules")

    return {
        "tenant_id": tenant_id,
        "name": name,
        "frequency": frequency,
        "starts_at": starts_at.isoformat(),
        "timezone": timezone_name,
        "audit_payload": audit_payload,
        "status": status,
        "weekdays": weekdays,
        "day_of_month": day_of_month,
    }


def _weekday_code(dt: datetime) -> str:
    return ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][dt.weekday()]


def _next_run_after(schedule: dict[str, Any], after_dt: datetime) -> datetime:
    starts_at = _parse_iso_datetime(schedule["starts_at"], "starts_at")
    frequency = schedule["frequency"]
    weekdays = schedule.get("weekdays", [])
    day_of_month = schedule.get("day_of_month")

    cursor = max(starts_at, after_dt)

    if frequency == FREQ_DAILY:
        if cursor <= starts_at:
            return starts_at
        base = starts_at
        while base <= after_dt:
            base = base + timedelta(days=1)
        return base

    if frequency == FREQ_WEEKLY:
        probe = cursor.replace(
            hour=starts_at.hour,
            minute=starts_at.minute,
            second=starts_at.second,
            microsecond=starts_at.microsecond,
        )
        if probe <= after_dt:
            probe = probe + timedelta(days=1)
        for _ in range(370):
            if probe >= starts_at and _weekday_code(probe) in weekdays:
                return probe
            probe = probe + timedelta(days=1)
            probe = probe.replace(
                hour=starts_at.hour,
                minute=starts_at.minute,
                second=starts_at.second,
                microsecond=starts_at.microsecond,
            )
        raise ValueError("unable to compute next weekly run")

    if frequency == FREQ_MONTHLY:
        probe = starts_at.replace(day=day_of_month)
        if probe <= after_dt:
            while probe <= after_dt:
                year = probe.year + (1 if probe.month == 12 else 0)
                month = 1 if probe.month == 12 else probe.month + 1
                probe = probe.replace(year=year, month=month, day=day_of_month)
        return probe

    raise ValueError(f"unsupported frequency: {frequency}")


def create_schedule(
    *,
    tenant_id: str,
    name: str,
    frequency: str,
    starts_at: str,
    timezone: str,
    audit_payload: dict[str, Any],
    weekdays: list[str] | None = None,
    day_of_month: int | None = None,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
    schedule_id = new_schedule_id()
    normalized = _validate_schedule_payload(
        {
            "tenant_id": tenant_id,
            "name": name,
            "frequency": frequency,
            "starts_at": starts_at,
            "timezone": timezone,
            "audit_payload": audit_payload,
            "weekdays": weekdays,
            "day_of_month": day_of_month,
            "status": STATUS_ACTIVE,
        }
    )

    next_run_at = _next_run_after(normalized, utc_now() - timedelta(seconds=1)).isoformat()
    payload = {
        "schedule_id": schedule_id,
        **normalized,
        "next_run_at": next_run_at,
        "last_run_at": None,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "deterministic_authoritative": True,
    }
    _atomic_write_json(_schedule_path(schedule_id, root), payload)
    return payload


def get_schedule(
    *,
    schedule_id: str,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
    path = _schedule_path(schedule_id, root)
    if not path.exists():
        raise FileNotFoundError(f"schedule not found: {schedule_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("schedule must be object")
    return payload


def list_schedules(root: Path = DEFAULT_SCHEDULE_ROOT) -> dict[str, Any]:
    if not root.exists():
        return {"count": 0, "items": [], "deterministic_authoritative": True}

    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("sch_*.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if isinstance(payload, dict):
            items.append(payload)

    items.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {
        "count": len(items),
        "items": items,
        "deterministic_authoritative": True,
    }


def update_schedule(
    *,
    schedule_id: str,
    name: str | None = None,
    frequency: str | None = None,
    starts_at: str | None = None,
    timezone: str | None = None,
    audit_payload: dict[str, Any] | None = None,
    weekdays: list[str] | None = None,
    day_of_month: int | None = None,
    status: str | None = None,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
    existing = get_schedule(schedule_id=schedule_id, root=root)

    merged = {
        "tenant_id": existing["tenant_id"],
        "name": name if name is not None else existing["name"],
        "frequency": frequency if frequency is not None else existing["frequency"],
        "starts_at": starts_at if starts_at is not None else existing["starts_at"],
        "timezone": timezone if timezone is not None else existing["timezone"],
        "audit_payload": audit_payload if audit_payload is not None else existing["audit_payload"],
        "weekdays": weekdays if weekdays is not None else existing.get("weekdays", []),
        "day_of_month": day_of_month if day_of_month is not None else existing.get("day_of_month"),
        "status": status if status is not None else existing["status"],
    }
    normalized = _validate_schedule_payload(merged)

    existing.update(normalized)
    existing["next_run_at"] = (
        _next_run_after(existing, utc_now() - timedelta(seconds=1)).isoformat()
        if existing["status"] == STATUS_ACTIVE
        else None
    )
    existing["updated_at"] = utc_now_iso()
    _atomic_write_json(_schedule_path(schedule_id, root), existing)
    return existing


def delete_schedule(
    *,
    schedule_id: str,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
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


def build_due_schedule_run_plan(
    *,
    as_of: datetime | None = None,
    limit: int = 50,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be positive int")
    as_of = as_of or utc_now()

    schedules = list_schedules(root)["items"]
    due: list[dict[str, Any]] = []
    for row in schedules:
        if not isinstance(row, dict):
            continue
        if row.get("status") != STATUS_ACTIVE:
            continue
        next_run_at = row.get("next_run_at")
        if not isinstance(next_run_at, str) or not next_run_at.strip():
            continue
        
        frequency = row.get("frequency")
        
        # For recurring schedules, compute the next run relative to as_of
        # to handle cases where the schedule wasn't executed but should be due
        if frequency in {FREQ_DAILY, FREQ_WEEKLY, FREQ_MONTHLY}:
            # Compute next run after the start time (or last run if available)
            last_run_at = row.get("last_run_at")
            if last_run_at:
                reference_dt = _parse_iso_datetime(last_run_at, "last_run_at")
            else:
                reference_dt = _parse_iso_datetime(row["starts_at"], "starts_at")
            
            # Find the next occurrence after the reference, then check if it's <= as_of
            computed_next = _next_run_after(row, reference_dt)
            
            # If the computed next run is <= as_of, the schedule is due
            if computed_next <= as_of:
                due.append(
                    {
                        "schedule_id": row["schedule_id"],
                        "tenant_id": row["tenant_id"],
                        "name": row["name"],
                        "audit_payload": row["audit_payload"],
                        "scheduled_for": computed_next.isoformat(),
                    }
                )
        else:
            # For non-recurring schedules, use the stored next_run_at
            next_dt = _parse_iso_datetime(next_run_at, "next_run_at")
            if next_dt <= as_of:
                due.append(
                    {
                        "schedule_id": row["schedule_id"],
                        "tenant_id": row["tenant_id"],
                        "name": row["name"],
                        "audit_payload": row["audit_payload"],
                        "scheduled_for": next_dt.isoformat(),
                    }
                )

    due.sort(key=lambda row: (row["scheduled_for"], row["schedule_id"]))
    return {
        "as_of": as_of.isoformat(),
        "candidate_count": len(due),
        "scheduled_count": min(limit, len(due)),
        "items": due[:limit],
        "deterministic_authoritative": True,
    }


def mark_schedule_run_executed(
    *,
    schedule_id: str,
    executed_at: str | None = None,
    root: Path = DEFAULT_SCHEDULE_ROOT,
) -> dict[str, Any]:
    payload = get_schedule(schedule_id=schedule_id, root=root)
    if payload["status"] != STATUS_ACTIVE:
        raise ValueError("only ACTIVE schedules can be executed")

    exec_dt = _parse_iso_datetime(executed_at, "executed_at") if executed_at else utc_now()
    payload["last_run_at"] = exec_dt.isoformat()
    payload["next_run_at"] = _next_run_after(payload, exec_dt).isoformat()
    payload["updated_at"] = utc_now_iso()
    _atomic_write_json(_schedule_path(schedule_id, root), payload)
    return payload
