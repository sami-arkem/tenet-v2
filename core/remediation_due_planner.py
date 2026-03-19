from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


REMEDIATION_DUE_PLANNER_SCHEMA_VERSION = "1.0"


def _stable_json_hash(payload: Dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        return None


@dataclass(frozen=True)
class PlannedNotificationEvent:
    event_id: str
    tenant_id: str
    remediation_id: str
    event_type: str
    recipient_user_ids: List[str]
    payload: Dict[str, object]
    created_at: str
    payload_hash: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def load_notification_outbox(path: Path) -> List[Dict[str, object]]:
    rows = _read_jsonl(path)
    rows.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["event_id"]))
    return rows


def write_notification_outbox(path: Path, rows: List[Dict[str, object]]) -> None:
    rows = sorted(rows, key=lambda row: (row["tenant_id"], row["created_at"], row["event_id"]))
    _write_jsonl(path, rows)


def plan_due_notifications(
    *,
    lifecycle_items: List[Dict[str, object]],
    existing_outbox: List[Dict[str, object]],
    today: str,
    now: str,
) -> List[Dict[str, object]]:
    today_dt = _parse_date(today)
    if today_dt is None:
        raise ValueError("Invalid today date")

    existing_event_ids = {str(row["event_id"]) for row in existing_outbox}
    outbox = list(existing_outbox)

    for row in lifecycle_items:
        status = str(row.get("status"))
        if status == "CLOSED":
            continue

        due_date_str = row.get("due_date")
        due_dt = _parse_date(str(due_date_str) if due_date_str is not None else None)
        if due_dt is None:
            continue

        owner = str(row.get("owner_user_id") or "")
        recipients = [owner] if owner else []

        if not recipients:
            continue

        delta = (due_dt.date() - today_dt.date()).days

        event_type: Optional[str] = None
        if delta < 0:
            event_type = "REMEDIATION_OVERDUE"
        elif 0 <= delta <= 7:
            event_type = "REMEDIATION_DUE_SOON"

        if event_type is None:
            continue

        event_id = f"{row['remediation_id']}:{event_type}:{today}"
        if event_id in existing_event_ids:
            continue

        payload = {
            "remediation_id": str(row["remediation_id"]),
            "audit_id": str(row["audit_id"]),
            "due_date": str(row["due_date"]),
            "status": status,
            "owner_user_id": owner,
            "days_until_due": delta,
        }
        row_payload = {
            "event_id": event_id,
            "tenant_id": str(row["tenant_id"]),
            "remediation_id": str(row["remediation_id"]),
            "event_type": event_type,
            "recipient_user_ids": recipients,
            "payload": payload,
            "created_at": now,
        }
        outbox.append(
            PlannedNotificationEvent(
                event_id=row_payload["event_id"],
                tenant_id=row_payload["tenant_id"],
                remediation_id=row_payload["remediation_id"],
                event_type=row_payload["event_type"],
                recipient_user_ids=row_payload["recipient_user_ids"],
                payload=row_payload["payload"],
                created_at=row_payload["created_at"],
                payload_hash=_stable_json_hash(row_payload),
            ).to_dict()
        )
        existing_event_ids.add(event_id)

    outbox.sort(key=lambda row: (row["tenant_id"], row["created_at"], row["event_id"]))
    return outbox
