from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


REMEDIATION_DASHBOARD_SCHEMA_VERSION = "1.0"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _first_day_of_month(today: str) -> str:
    dt = datetime.strptime(today, "%Y-%m-%d")
    return dt.replace(day=1).date().isoformat()


@dataclass(frozen=True)
class RemediationDashboardRow:
    remediation_id: str
    audit_id: str
    tenant_id: str
    audit_kind: str
    title: str
    severity: str
    status: str
    owner_user_id: Optional[str]
    due_date: Optional[str]
    release_blocking: bool
    overdue: bool
    due_in_7_days: bool
    assigned_to_current_user: bool
    sort_bucket: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationDashboardSummary:
    schema_version: str
    open_count: int
    in_progress_count: int
    overdue_count: int
    closed_this_month_count: int
    rows: List[RemediationDashboardRow]
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "open_count": self.open_count,
            "in_progress_count": self.in_progress_count,
            "overdue_count": self.overdue_count,
            "closed_this_month_count": self.closed_this_month_count,
            "rows": [row.to_dict() for row in self.rows],
            "payload_hash": self.payload_hash,
        }


def _is_overdue(row: Dict[str, object], today: str) -> bool:
    due_date = str(row.get("due_date") or "")
    status = str(row.get("status") or "")
    return bool(due_date) and due_date < today and status != "CLOSED"


def _is_due_in_7_days(row: Dict[str, object], today: str) -> bool:
    due_date = _parse_date(str(row.get("due_date") or ""))
    if due_date is None or str(row.get("status")) == "CLOSED":
        return False
    today_dt = _parse_date(today)
    if today_dt is None:
        return False
    delta = (due_date.date() - today_dt.date()).days
    return 0 <= delta <= 7


def _closed_this_month(row: Dict[str, object], today: str) -> bool:
    closed_at = str(row.get("closed_at") or "")
    if str(row.get("status")) != "CLOSED" or not closed_at:
        return False
    closed_dt = _parse_date(closed_at)
    if closed_dt is None:
        return False
    return closed_dt.date().isoformat() >= _first_day_of_month(today)


def _sort_bucket(
    *,
    assigned_to_current_user: bool,
    overdue: bool,
    due_in_7_days: bool,
) -> str:
    if assigned_to_current_user:
        return "ASSIGNED_TO_ME"
    if overdue:
        return "OVERDUE"
    if due_in_7_days:
        return "DUE_SOON"
    return "NORMAL"


def _sort_key(row: RemediationDashboardRow) -> tuple:
    bucket_rank = {
        "ASSIGNED_TO_ME": 0,
        "OVERDUE": 1,
        "DUE_SOON": 2,
        "NORMAL": 3,
    }[row.sort_bucket]
    due_date = row.due_date or "9999-12-31"
    return (
        bucket_rank,
        due_date,
        row.severity,
        row.remediation_id,
    )


def build_remediation_dashboard(
    *,
    lifecycle_items: List[Dict[str, object]],
    actor_user_id: str,
    tenant_id: str,
    today: str,
) -> RemediationDashboardSummary:
    scoped_rows = [row for row in lifecycle_items if str(row.get("tenant_id")) == tenant_id]

    dashboard_rows: List[RemediationDashboardRow] = []
    for row in scoped_rows:
        overdue = _is_overdue(row, today)
        due_in_7_days = _is_due_in_7_days(row, today)
        assigned_to_current_user = str(row.get("owner_user_id") or "") == actor_user_id
        sort_bucket = _sort_bucket(
            assigned_to_current_user=assigned_to_current_user,
            overdue=overdue,
            due_in_7_days=due_in_7_days,
        )
        payload = {
            "remediation_id": str(row["remediation_id"]),
            "audit_id": str(row["audit_id"]),
            "tenant_id": str(row["tenant_id"]),
            "audit_kind": str(row["audit_kind"]),
            "title": str(row["title"]),
            "severity": str(row["severity"]),
            "status": str(row["status"]),
            "owner_user_id": row.get("owner_user_id"),
            "due_date": row.get("due_date"),
            "release_blocking": bool(row.get("release_blocking", False)),
            "overdue": overdue,
            "due_in_7_days": due_in_7_days,
            "assigned_to_current_user": assigned_to_current_user,
            "sort_bucket": sort_bucket,
        }
        dashboard_rows.append(
            RemediationDashboardRow(
                remediation_id=payload["remediation_id"],
                audit_id=payload["audit_id"],
                tenant_id=payload["tenant_id"],
                audit_kind=payload["audit_kind"],
                title=payload["title"],
                severity=payload["severity"],
                status=payload["status"],
                owner_user_id=payload["owner_user_id"],
                due_date=payload["due_date"],
                release_blocking=payload["release_blocking"],
                overdue=payload["overdue"],
                due_in_7_days=payload["due_in_7_days"],
                assigned_to_current_user=payload["assigned_to_current_user"],
                sort_bucket=payload["sort_bucket"],
                payload_hash=_stable_json_hash(payload),
            )
        )

    dashboard_rows.sort(key=_sort_key)

    payload = {
        "schema_version": REMEDIATION_DASHBOARD_SCHEMA_VERSION,
        "open_count": sum(1 for row in scoped_rows if str(row.get("status")) == "OPEN"),
        "in_progress_count": sum(1 for row in scoped_rows if str(row.get("status")) == "IN_PROGRESS"),
        "overdue_count": sum(1 for row in scoped_rows if _is_overdue(row, today)),
        "closed_this_month_count": sum(1 for row in scoped_rows if _closed_this_month(row, today)),
        "rows": [row.to_dict() for row in dashboard_rows],
    }

    return RemediationDashboardSummary(
        schema_version=payload["schema_version"],
        open_count=payload["open_count"],
        in_progress_count=payload["in_progress_count"],
        overdue_count=payload["overdue_count"],
        closed_this_month_count=payload["closed_this_month_count"],
        rows=dashboard_rows,
        payload_hash=_stable_json_hash(payload),
    )
