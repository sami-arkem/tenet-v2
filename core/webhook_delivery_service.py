from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


DEFAULT_WEBHOOK_ROOT = Path("fixtures") / "webhooks"

EVENT_AUDIT_COMPLETED = "audit.completed"
EVENT_AUDIT_FAILED = "audit.failed"
EVENT_FINDING_CREATED = "finding.created"
EVENT_FINDING_STATUS_CHANGED = "finding.status_changed"
EVENT_FINDING_OVERDUE = "finding.overdue"
EVENT_REGULATORY_ALERT = "regulatory.alert"
EVENT_REMEDIATION_VERIFIED = "remediation.verified"

ALLOWED_WEBHOOK_EVENTS = {
    EVENT_AUDIT_COMPLETED,
    EVENT_AUDIT_FAILED,
    EVENT_FINDING_CREATED,
    EVENT_FINDING_STATUS_CHANGED,
    EVENT_FINDING_OVERDUE,
    EVENT_REGULATORY_ALERT,
    EVENT_REMEDIATION_VERIFIED,
}

STATUS_ACTIVE = "ACTIVE"
STATUS_DISABLED = "DISABLED"

DELIVERY_QUEUED = "QUEUED"
DELIVERY_SENT = "SENT"
DELIVERY_FAILED = "FAILED"

MAX_CONSECUTIVE_FAILURES = 10
RETRY_BACKOFF_SECONDS = [60, 300, 1800]


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


def _webhook_path(webhook_id: str, root: Path = DEFAULT_WEBHOOK_ROOT) -> Path:
    return root / "definitions" / f"{_require_non_empty_str(webhook_id, 'webhook_id')}.json"


def _delivery_path(delivery_id: str, root: Path = DEFAULT_WEBHOOK_ROOT) -> Path:
    return root / "deliveries" / f"{_require_non_empty_str(delivery_id, 'delivery_id')}.json"


def _delivery_log_path(root: Path = DEFAULT_WEBHOOK_ROOT) -> Path:
    return root / "delivery_log.json"


def _new_webhook_id() -> str:
    return f"wh_{uuid.uuid4().hex[:16]}"


def _new_delivery_id() -> str:
    return f"whd_{uuid.uuid4().hex[:16]}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sign_payload(secret: str, payload_bytes: bytes) -> str:
    secret = _require_non_empty_str(secret, "secret")
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _load_delivery_log(root: Path = DEFAULT_WEBHOOK_ROOT) -> dict[str, Any]:
    path = _delivery_log_path(root)
    if not path.exists():
        return {"items": []}
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("delivery log must be object")
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def _write_delivery_log(payload: dict[str, Any], root: Path = DEFAULT_WEBHOOK_ROOT) -> None:
    _atomic_write_json(_delivery_log_path(root), payload)


def create_webhook(
    *,
    name: str,
    target_url: str,
    secret: str,
    event_types: list[str],
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    name = _require_non_empty_str(name, "name")
    target_url = _require_non_empty_str(target_url, "target_url")
    secret = _require_non_empty_str(secret, "secret")
    event_types = [str(item).strip() for item in _require_list(event_types, "event_types") if str(item).strip()]
    if not event_types:
        raise ValueError("event_types must be non-empty")
    for event_type in event_types:
        if event_type not in ALLOWED_WEBHOOK_EVENTS:
            raise ValueError(f"unsupported webhook event type: {event_type}")

    webhook_id = _new_webhook_id()
    payload = {
        "webhook_id": webhook_id,
        "name": name,
        "target_url": target_url,
        "secret": secret,
        "event_types": sorted(set(event_types)),
        "status": STATUS_ACTIVE,
        "consecutive_failures": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "deterministic_authoritative": True,
    }
    _atomic_write_json(_webhook_path(webhook_id, root), payload)
    return payload


def get_webhook(
    *,
    webhook_id: str,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    path = _webhook_path(webhook_id, root)
    if not path.exists():
        raise FileNotFoundError(f"webhook not found: {webhook_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("webhook definition must be object")
    return payload


def list_webhooks(root: Path = DEFAULT_WEBHOOK_ROOT) -> dict[str, Any]:
    base = root / "definitions"
    if not base.exists():
        return {"count": 0, "items": [], "deterministic_authoritative": True}

    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("wh_*.json")):
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


def update_webhook(
    *,
    webhook_id: str,
    name: str | None = None,
    target_url: str | None = None,
    secret: str | None = None,
    event_types: list[str] | None = None,
    status: str | None = None,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    payload = get_webhook(webhook_id=webhook_id, root=root)

    if name is not None:
        payload["name"] = _require_non_empty_str(name, "name")
    if target_url is not None:
        payload["target_url"] = _require_non_empty_str(target_url, "target_url")
    if secret is not None:
        payload["secret"] = _require_non_empty_str(secret, "secret")
    if event_types is not None:
        cleaned = [str(item).strip() for item in event_types if str(item).strip()]
        if not cleaned:
            raise ValueError("event_types must be non-empty when provided")
        for event_type in cleaned:
            if event_type not in ALLOWED_WEBHOOK_EVENTS:
                raise ValueError(f"unsupported webhook event type: {event_type}")
        payload["event_types"] = sorted(set(cleaned))
    if status is not None:
        normalized_status = _require_non_empty_str(status, "status")
        if normalized_status not in {STATUS_ACTIVE, STATUS_DISABLED}:
            raise ValueError("status must be ACTIVE or DISABLED")
        payload["status"] = normalized_status

    payload["updated_at"] = _now_iso()
    _atomic_write_json(_webhook_path(webhook_id, root), payload)
    return payload


def delete_webhook(
    *,
    webhook_id: str,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    path = _webhook_path(webhook_id, root)
    if not path.exists():
        raise FileNotFoundError(f"webhook not found: {webhook_id}")
    payload = _load_json(path)
    path.unlink()
    return {
        "webhook_id": webhook_id,
        "deleted": True,
        "previous": payload,
        "deterministic_authoritative": True,
    }


def queue_webhook_delivery(
    *,
    event_type: str,
    payload: dict[str, Any],
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    event_type = _require_non_empty_str(event_type, "event_type")
    if event_type not in ALLOWED_WEBHOOK_EVENTS:
        raise ValueError(f"unsupported webhook event type: {event_type}")
    payload = _require_dict(payload, "payload")

    webhooks = list_webhooks(root=root)["items"]
    deliveries: list[dict[str, Any]] = []

    for webhook in webhooks:
        if webhook.get("status") != STATUS_ACTIVE:
            continue
        if event_type not in webhook.get("event_types", []):
            continue

        delivery_id = _new_delivery_id()
        event_payload = {
            "event": event_type,
            "delivery_id": delivery_id,
            "created_at": _now_iso(),
            "payload": payload,
        }
        body_bytes = json.dumps(event_payload, sort_keys=True).encode("utf-8")
        signature = _sign_payload(webhook["secret"], body_bytes)

        delivery = {
            "delivery_id": delivery_id,
            "webhook_id": webhook["webhook_id"],
            "event_type": event_type,
            "target_url": webhook["target_url"],
            "status": DELIVERY_QUEUED,
            "attempt_count": 0,
            "next_attempt_at": _now_iso(),
            "last_attempt_at": None,
            "response_status_code": None,
            "failure_reason": None,
            "headers": {
                "X-Tenet-Signature": signature,
                "X-Tenet-Event": event_type,
                "X-Tenet-Delivery": delivery_id,
            },
            "body": event_payload,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "deterministic_authoritative": True,
        }
        _atomic_write_json(_delivery_path(delivery_id, root), delivery)
        deliveries.append(delivery)

    return {
        "event_type": event_type,
        "delivery_count": len(deliveries),
        "deliveries": deliveries,
        "deterministic_authoritative": True,
    }


def _simulate_send(delivery: dict[str, Any]) -> tuple[int, str | None]:
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be object")
    return 200, None


def dispatch_webhook_delivery(
    *,
    delivery_id: str,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    path = _delivery_path(delivery_id, root)
    if not path.exists():
        raise FileNotFoundError(f"webhook delivery not found: {delivery_id}")

    delivery = _load_json(path)
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be object")

    webhook = get_webhook(webhook_id=delivery["webhook_id"], root=root)
    if webhook["status"] != STATUS_ACTIVE:
        delivery["status"] = DELIVERY_FAILED
        delivery["failure_reason"] = "webhook_disabled"
        delivery["updated_at"] = _now_iso()
        _atomic_write_json(path, delivery)
        return delivery

    status_code, failure_reason = _simulate_send(delivery)
    delivery["attempt_count"] = int(delivery.get("attempt_count", 0)) + 1
    delivery["last_attempt_at"] = _now_iso()
    delivery["response_status_code"] = status_code

    if 200 <= status_code < 300 and failure_reason is None:
        delivery["status"] = DELIVERY_SENT
        delivery["failure_reason"] = None
        webhook["consecutive_failures"] = 0
    else:
        delivery["status"] = DELIVERY_FAILED
        delivery["failure_reason"] = failure_reason or f"http_{status_code}"
        failures = int(webhook.get("consecutive_failures", 0)) + 1
        webhook["consecutive_failures"] = failures
        if failures >= MAX_CONSECUTIVE_FAILURES:
            webhook["status"] = STATUS_DISABLED
        attempt_count = delivery["attempt_count"]
        if attempt_count <= len(RETRY_BACKOFF_SECONDS):
            delivery["next_attempt_at"] = _now_iso()

    delivery["updated_at"] = _now_iso()
    webhook["updated_at"] = _now_iso()
    _atomic_write_json(path, delivery)
    _atomic_write_json(_webhook_path(webhook["webhook_id"], root), webhook)

    log = _load_delivery_log(root)
    log["items"].append(
        {
            "delivery_id": delivery["delivery_id"],
            "webhook_id": webhook["webhook_id"],
            "event_type": delivery["event_type"],
            "status": delivery["status"],
            "response_status_code": delivery["response_status_code"],
            "failure_reason": delivery["failure_reason"],
            "attempt_count": delivery["attempt_count"],
            "logged_at": _now_iso(),
        }
    )
    _write_delivery_log(log, root)
    return delivery


def get_webhook_delivery(
    *,
    delivery_id: str,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    path = _delivery_path(delivery_id, root)
    if not path.exists():
        raise FileNotFoundError(f"webhook delivery not found: {delivery_id}")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("delivery must be object")
    return payload


def list_webhook_deliveries(root: Path = DEFAULT_WEBHOOK_ROOT) -> dict[str, Any]:
    base = root / "deliveries"
    if not base.exists():
        return {"count": 0, "items": [], "deterministic_authoritative": True}

    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("whd_*.json")):
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


def send_test_webhook_delivery(
    *,
    webhook_id: str,
    root: Path = DEFAULT_WEBHOOK_ROOT,
) -> dict[str, Any]:
    webhook = get_webhook(webhook_id=webhook_id, root=root)
    queued = queue_webhook_delivery(
        event_type=EVENT_AUDIT_COMPLETED,
        payload={
            "test": True,
            "webhook_id": webhook_id,
            "message": "This is a test delivery.",
        },
        root=root,
    )
    matches = [item for item in queued["deliveries"] if item["webhook_id"] == webhook["webhook_id"]]
    if not matches:
        raise ValueError("no test delivery queued for webhook")
    delivery_id = matches[0]["delivery_id"]
    return dispatch_webhook_delivery(delivery_id=delivery_id, root=root)
