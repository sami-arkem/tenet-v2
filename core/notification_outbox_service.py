from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_NOTIFICATION_ROOT = Path("fixtures") / "notifications"


EVENT_AUDIT_COMPLETE = "AUDIT_COMPLETE"
EVENT_AUDIT_FAILED = "AUDIT_FAILED"
EVENT_FINDING_ASSIGNED = "FINDING_ASSIGNED"
EVENT_REMEDIATION_VERIFIED = "REMEDIATION_VERIFIED"
EVENT_REMEDIATION_FAILED = "REMEDIATION_FAILED"
EVENT_REGULATORY_ALERT_HIGH = "REGULATORY_ALERT_HIGH"
EVENT_REPORT_GENERATED = "REPORT_GENERATED"
EVENT_OVERDUE_FINDINGS_DIGEST = "OVERDUE_FINDINGS_DIGEST"
EVENT_UPCOMING_DUE_DATES = "UPCOMING_DUE_DATES"
EVENT_WEEKLY_POSTURE_SUMMARY = "WEEKLY_POSTURE_SUMMARY"

ALLOWED_EVENT_TYPES = {
    EVENT_AUDIT_COMPLETE,
    EVENT_AUDIT_FAILED,
    EVENT_FINDING_ASSIGNED,
    EVENT_REMEDIATION_VERIFIED,
    EVENT_REMEDIATION_FAILED,
    EVENT_REGULATORY_ALERT_HIGH,
    EVENT_REPORT_GENERATED,
    EVENT_OVERDUE_FINDINGS_DIGEST,
    EVENT_UPCOMING_DUE_DATES,
    EVENT_WEEKLY_POSTURE_SUMMARY,
}

CHANNEL_EMAIL = "email"
CHANNEL_IN_APP = "in_app"
ALLOWED_CHANNELS = {CHANNEL_EMAIL, CHANNEL_IN_APP}

STATUS_QUEUED = "QUEUED"
STATUS_SENT = "SENT"
STATUS_SKIPPED = "SKIPPED"
STATUS_FAILED = "FAILED"

DEFAULT_NOTIFICATION_PREFERENCES = {
    "audit_complete": {"email": True, "in_app": True},
    "finding_assigned": {"email": True, "in_app": True},
    "finding_overdue": {"email": True, "in_app": True},
    "regulatory_alert": {"email": True, "in_app": True},
    "weekly_summary": {"email": False, "in_app": True},
    "digest_time": "07:00",
    "timezone": "Europe/London",
}

EVENT_TO_PREFERENCE_KEY = {
    EVENT_AUDIT_COMPLETE: "audit_complete",
    EVENT_AUDIT_FAILED: "audit_complete",
    EVENT_FINDING_ASSIGNED: "finding_assigned",
    EVENT_REMEDIATION_VERIFIED: "finding_assigned",
    EVENT_REMEDIATION_FAILED: "finding_assigned",
    EVENT_REGULATORY_ALERT_HIGH: "regulatory_alert",
    EVENT_REPORT_GENERATED: "audit_complete",
    EVENT_OVERDUE_FINDINGS_DIGEST: "finding_overdue",
    EVENT_UPCOMING_DUE_DATES: "finding_overdue",
    EVENT_WEEKLY_POSTURE_SUMMARY: "weekly_summary",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_notification_id() -> str:
    return f"notif_{uuid.uuid4().hex[:16]}"


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


def _notification_path(notification_id: str, root: Path = DEFAULT_NOTIFICATION_ROOT) -> Path:
    notification_id = _require_non_empty_str(notification_id, "notification_id")
    return root / "outbox" / f"{notification_id}.json"


def _delivery_log_path(root: Path = DEFAULT_NOTIFICATION_ROOT) -> Path:
    return root / "notification_log.json"


def _coerce_recipients(recipients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(recipients):
        row = _require_dict(row, f"recipients[{idx}]")
        user_id = _require_non_empty_str(row.get("user_id"), f"recipients[{idx}].user_id")
        preferences = row.get("notification_preferences")
        if preferences is None:
            preferences = dict(DEFAULT_NOTIFICATION_PREFERENCES)
        preferences = _require_dict(preferences, f"recipients[{idx}].notification_preferences")
        rows.append(
            {
                "user_id": user_id,
                "email": row.get("email"),
                "notification_preferences": preferences,
            }
        )
    return rows


def _preference_allows_channel(event_type: str, channel: str, preferences: dict[str, Any]) -> bool:
    preference_key = EVENT_TO_PREFERENCE_KEY.get(event_type)
    if not preference_key:
        return False
    block = preferences.get(preference_key)
    if not isinstance(block, dict):
        return False
    return block.get(channel) is True


def _render_subject(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == EVENT_REGULATORY_ALERT_HIGH:
        return f"[Tenet] High-priority regulatory alert: {payload.get('title') or 'Update detected'}"
    if event_type == EVENT_AUDIT_COMPLETE:
        return f"[Tenet] Audit complete: {payload.get('run_id') or 'Run'}"
    if event_type == EVENT_AUDIT_FAILED:
        return f"[Tenet] Audit failed: {payload.get('run_id') or 'Run'}"
    if event_type == EVENT_REPORT_GENERATED:
        return f"[Tenet] Report generated: {payload.get('run_id') or 'Run'}"
    if event_type == EVENT_WEEKLY_POSTURE_SUMMARY:
        return "[Tenet] Weekly posture summary"
    if event_type == EVENT_OVERDUE_FINDINGS_DIGEST:
        return "[Tenet] Overdue findings digest"
    if event_type == EVENT_UPCOMING_DUE_DATES:
        return "[Tenet] Upcoming due dates"
    if event_type == EVENT_FINDING_ASSIGNED:
        return f"[Tenet] Finding assigned: {payload.get('finding_id') or 'Finding'}"
    if event_type == EVENT_REMEDIATION_VERIFIED:
        return f"[Tenet] Remediation verified: {payload.get('finding_id') or 'Finding'}"
    if event_type == EVENT_REMEDIATION_FAILED:
        return f"[Tenet] Remediation failed: {payload.get('finding_id') or 'Finding'}"
    raise ValueError(f"unsupported event_type: {event_type}")


def _render_body(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == EVENT_REGULATORY_ALERT_HIGH:
        return (
            "Regulatory alert detected.\n"
            f"Title: {payload.get('title')}\n"
            f"Summary: {payload.get('summary')}\n"
            f"Affected controls: {', '.join(payload.get('controls_to_review', []))}\n"
            f"Jurisdictions: {', '.join(payload.get('jurisdictions', []))}\n"
        )
    if event_type == EVENT_AUDIT_COMPLETE:
        return (
            "Audit completed.\n"
            f"Run ID: {payload.get('run_id')}\n"
            f"Overall posture: {payload.get('overall_posture')}\n"
            f"Deployment decision: {payload.get('deployment_decision')}\n"
        )
    if event_type == EVENT_AUDIT_FAILED:
        return (
            "Audit failed.\n"
            f"Run ID: {payload.get('run_id')}\n"
            f"Failure reason: {payload.get('failure_reason')}\n"
        )
    if event_type == EVENT_REPORT_GENERATED:
        return (
            "Report generated.\n"
            f"Run ID: {payload.get('run_id')}\n"
            f"Format: {payload.get('format')}\n"
        )
    if event_type == EVENT_FINDING_ASSIGNED:
        return (
            "Finding assigned.\n"
            f"Finding ID: {payload.get('finding_id')}\n"
            f"Priority: {payload.get('priority')}\n"
            f"Action required: {payload.get('action_required')}\n"
        )
    if event_type == EVENT_REMEDIATION_VERIFIED:
        return (
            "Remediation verified.\n"
            f"Finding ID: {payload.get('finding_id')}\n"
            "Status: VERIFIED\n"
        )
    if event_type == EVENT_REMEDIATION_FAILED:
        return (
            "Remediation failed.\n"
            f"Finding ID: {payload.get('finding_id')}\n"
            f"Reason: {payload.get('reason')}\n"
        )
    if event_type == EVENT_OVERDUE_FINDINGS_DIGEST:
        return (
            "Overdue findings digest.\n"
            f"Overdue count: {payload.get('overdue_count')}\n"
            f"Finding IDs: {', '.join(payload.get('finding_ids', []))}\n"
        )
    if event_type == EVENT_UPCOMING_DUE_DATES:
        return (
            "Upcoming due dates.\n"
            f"Due soon count: {payload.get('due_soon_count')}\n"
            f"Finding IDs: {', '.join(payload.get('finding_ids', []))}\n"
        )
    if event_type == EVENT_WEEKLY_POSTURE_SUMMARY:
        return (
            "Weekly posture summary.\n"
            f"Overall posture: {payload.get('overall_posture')}\n"
            f"Open findings: {payload.get('open_findings')}\n"
        )
    raise ValueError(f"unsupported event_type: {event_type}")


def queue_notification_event(
    *,
    event_type: str,
    payload: dict[str, Any],
    recipients: list[dict[str, Any]],
    channels: list[str] | None = None,
    root: Path = DEFAULT_NOTIFICATION_ROOT,
) -> dict[str, Any]:
    event_type = _require_non_empty_str(event_type, "event_type")
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")

    payload = _require_dict(payload, "payload")
    recipients = _coerce_recipients(_require_list(recipients, "recipients"))

    if channels is None:
        channels = [CHANNEL_EMAIL, CHANNEL_IN_APP]
    if not isinstance(channels, list) or not channels:
        raise ValueError("channels must be non-empty list")
    normalized_channels: list[str] = []
    for idx, channel in enumerate(channels):
        normalized = _require_non_empty_str(channel, f"channels[{idx}]")
        if normalized not in ALLOWED_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(ALLOWED_CHANNELS)}")
        normalized_channels.append(normalized)

    notification_id = new_notification_id()
    created_at = utc_now_iso()
    subject = _render_subject(event_type, payload)
    body = _render_body(event_type, payload)

    deliveries: list[dict[str, Any]] = []
    for recipient in recipients:
        preferences = recipient["notification_preferences"]
        for channel in normalized_channels:
            allowed = _preference_allows_channel(event_type, channel, preferences)
            deliveries.append(
                {
                    "user_id": recipient["user_id"],
                    "email": recipient.get("email"),
                    "channel": channel,
                    "status": STATUS_QUEUED if allowed else STATUS_SKIPPED,
                    "skip_reason": None if allowed else "preference_disabled",
                    "attempt_count": 0,
                    "last_attempt_at": None,
                    "delivered_at": None,
                }
            )

    notification = {
        "notification_id": notification_id,
        "event_type": event_type,
        "payload": payload,
        "subject": subject,
        "body": body,
        "status": STATUS_QUEUED,
        "deliveries": deliveries,
        "created_at": created_at,
        "updated_at": created_at,
        "deterministic_authoritative": True,
    }
    _atomic_write_json(_notification_path(notification_id, root), notification)
    return notification


def _load_delivery_log(root: Path = DEFAULT_NOTIFICATION_ROOT) -> dict[str, Any]:
    path = _delivery_log_path(root)
    if not path.exists():
        return {"items": []}
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("notification log must be object")
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def _write_delivery_log(payload: dict[str, Any], root: Path = DEFAULT_NOTIFICATION_ROOT) -> None:
    _atomic_write_json(_delivery_log_path(root), payload)


def dispatch_notification(
    *,
    notification_id: str,
    root: Path = DEFAULT_NOTIFICATION_ROOT,
) -> dict[str, Any]:
    path = _notification_path(notification_id, root)
    if not path.exists():
        raise FileNotFoundError(f"notification not found: {notification_id}")

    notification = _load_json(path)
    if not isinstance(notification, dict):
        raise ValueError("notification must be object")

    deliveries = notification.get("deliveries", [])
    if not isinstance(deliveries, list):
        raise ValueError("notification.deliveries must be list")

    log = _load_delivery_log(root)
    log_items = log["items"]

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for delivery in deliveries:
        if not isinstance(delivery, dict):
            continue
        if delivery.get("status") == STATUS_SKIPPED:
            skipped_count += 1
            log_items.append(
                {
                    "notification_id": notification_id,
                    "user_id": delivery.get("user_id"),
                    "channel": delivery.get("channel"),
                    "status": STATUS_SKIPPED,
                    "logged_at": utc_now_iso(),
                }
            )
            continue

        try:
            delivery["attempt_count"] = int(delivery.get("attempt_count", 0)) + 1
            delivery["last_attempt_at"] = utc_now_iso()
            delivery["status"] = STATUS_SENT
            delivery["delivered_at"] = utc_now_iso()
            sent_count += 1
            log_items.append(
                {
                    "notification_id": notification_id,
                    "user_id": delivery.get("user_id"),
                    "channel": delivery.get("channel"),
                    "status": STATUS_SENT,
                    "logged_at": utc_now_iso(),
                }
            )
        except Exception:
            delivery["status"] = STATUS_FAILED
            failed_count += 1
            log_items.append(
                {
                    "notification_id": notification_id,
                    "user_id": delivery.get("user_id"),
                    "channel": delivery.get("channel"),
                    "status": STATUS_FAILED,
                    "logged_at": utc_now_iso(),
                }
            )

    if failed_count > 0:
        notification["status"] = STATUS_FAILED
    elif sent_count > 0:
        notification["status"] = STATUS_SENT
    else:
        notification["status"] = STATUS_SKIPPED

    notification["updated_at"] = utc_now_iso()
    _atomic_write_json(path, notification)
    _write_delivery_log(log, root)

    return {
        "notification_id": notification_id,
        "status": notification["status"],
        "sent_count": sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "deliveries": deliveries,
        "deterministic_authoritative": True,
    }


def queue_regulatory_alert_notification(
    *,
    alert_payload: dict[str, Any],
    recipients: list[dict[str, Any]],
    root: Path = DEFAULT_NOTIFICATION_ROOT,
) -> dict[str, Any]:
    alert_payload = _require_dict(alert_payload, "alert_payload")
    return queue_notification_event(
        event_type=EVENT_REGULATORY_ALERT_HIGH,
        payload=alert_payload,
        recipients=recipients,
        channels=[CHANNEL_EMAIL, CHANNEL_IN_APP],
        root=root,
    )


def list_notifications(root: Path = DEFAULT_NOTIFICATION_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    outbox = root / "outbox"
    if not outbox.exists():
        return {"count": 0, "items": [], "deterministic_authoritative": True}

    for path in sorted(outbox.glob("notif_*.json")):
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


def get_notification(notification_id: str, root: Path = DEFAULT_NOTIFICATION_ROOT) -> dict[str, Any]:
    path = _notification_path(notification_id, root)
    if not path.exists():
        raise FileNotFoundError(f"notification not found: {notification_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("notification must be object")
    return payload
