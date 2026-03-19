from __future__ import annotations

from pathlib import Path

from core.webhook_delivery_service import (
    EVENT_AUDIT_COMPLETED,
    EVENT_REGULATORY_ALERT,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    create_webhook,
    delete_webhook,
    dispatch_webhook_delivery,
    get_webhook,
    get_webhook_delivery,
    list_webhook_deliveries,
    list_webhooks,
    queue_webhook_delivery,
    send_test_webhook_delivery,
    update_webhook,
)


def test_webhook_crud_and_queue_dispatch(tmp_path: Path):
    webhook = create_webhook(
        name="Audit Webhook",
        target_url="https://example.com/webhook",
        secret="supersecret",
        event_types=[EVENT_AUDIT_COMPLETED, EVENT_REGULATORY_ALERT],
        root=tmp_path,
    )
    assert webhook["status"] == STATUS_ACTIVE

    loaded = get_webhook(webhook_id=webhook["webhook_id"], root=tmp_path)
    assert loaded["webhook_id"] == webhook["webhook_id"]

    updated = update_webhook(
        webhook_id=webhook["webhook_id"],
        name="Updated Audit Webhook",
        root=tmp_path,
    )
    assert updated["name"] == "Updated Audit Webhook"

    queued = queue_webhook_delivery(
        event_type=EVENT_AUDIT_COMPLETED,
        payload={"run_id": "run_001", "overall_posture": "GREEN"},
        root=tmp_path,
    )
    assert queued["delivery_count"] == 1
    delivery_id = queued["deliveries"][0]["delivery_id"]

    delivery = dispatch_webhook_delivery(delivery_id=delivery_id, root=tmp_path)
    assert delivery["status"] == "SENT"
    assert delivery["response_status_code"] == 200

    loaded_delivery = get_webhook_delivery(delivery_id=delivery_id, root=tmp_path)
    assert loaded_delivery["delivery_id"] == delivery_id

    deliveries = list_webhook_deliveries(root=tmp_path)
    assert deliveries["count"] == 1

    test_delivery = send_test_webhook_delivery(webhook_id=webhook["webhook_id"], root=tmp_path)
    assert test_delivery["status"] == "SENT"

    deleted = delete_webhook(webhook_id=webhook["webhook_id"], root=tmp_path)
    assert deleted["deleted"] is True

    listed = list_webhooks(root=tmp_path)
    assert listed["count"] == 0


def test_disable_after_consecutive_failures(tmp_path: Path, monkeypatch):
    webhook = create_webhook(
        name="Failing Webhook",
        target_url="https://example.com/fail",
        secret="supersecret",
        event_types=[EVENT_AUDIT_COMPLETED],
        root=tmp_path,
    )

    from core import webhook_delivery_service as svc

    monkeypatch.setattr(svc, "_simulate_send", lambda delivery: (500, "server_error"))

    last_delivery_id = None
    for idx in range(10):
        queued = queue_webhook_delivery(
            event_type=EVENT_AUDIT_COMPLETED,
            payload={"run_id": f"run_{idx}"},
            root=tmp_path,
        )
        last_delivery_id = queued["deliveries"][0]["delivery_id"]
        dispatch_webhook_delivery(delivery_id=last_delivery_id, root=tmp_path)

    loaded = get_webhook(webhook_id=webhook["webhook_id"], root=tmp_path)
    assert loaded["status"] == STATUS_DISABLED
    assert loaded["consecutive_failures"] >= 10
