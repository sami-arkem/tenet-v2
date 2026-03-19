from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_webhooks_api_flow(tmp_path, monkeypatch):
    from api.routers import webhooks as webhooks_router
    from core.webhook_delivery_service import (
        create_webhook as service_create_webhook,
        delete_webhook as service_delete_webhook,
        dispatch_webhook_delivery as service_dispatch_webhook_delivery,
        get_webhook as service_get_webhook,
        get_webhook_delivery as service_get_webhook_delivery,
        list_webhook_deliveries as service_list_webhook_deliveries,
        list_webhooks as service_list_webhooks,
        queue_webhook_delivery as service_queue_webhook_delivery,
        send_test_webhook_delivery as service_send_test_webhook_delivery,
        update_webhook as service_update_webhook,
    )

    monkeypatch.setattr(
        webhooks_router,
        "create_webhook",
        lambda name, target_url, secret, event_types: service_create_webhook(
            name=name,
            target_url=target_url,
            secret=secret,
            event_types=event_types,
            root=tmp_path,
        ),
    )
    monkeypatch.setattr(webhooks_router, "list_webhooks", lambda: service_list_webhooks(root=tmp_path))
    monkeypatch.setattr(
        webhooks_router,
        "get_webhook",
        lambda webhook_id: service_get_webhook(webhook_id=webhook_id, root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "queue_webhook_delivery",
        lambda event_type, payload: service_queue_webhook_delivery(event_type=event_type, payload=payload, root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "dispatch_webhook_delivery",
        lambda delivery_id: service_dispatch_webhook_delivery(delivery_id=delivery_id, root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "list_webhook_deliveries",
        lambda: service_list_webhook_deliveries(root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "get_webhook_delivery",
        lambda delivery_id: service_get_webhook_delivery(delivery_id=delivery_id, root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "send_test_webhook_delivery",
        lambda webhook_id: service_send_test_webhook_delivery(webhook_id=webhook_id, root=tmp_path),
    )
    monkeypatch.setattr(
        webhooks_router,
        "update_webhook",
        lambda webhook_id, name=None, target_url=None, secret=None, event_types=None, status=None: service_update_webhook(
            webhook_id=webhook_id,
            name=name,
            target_url=target_url,
            secret=secret,
            event_types=event_types,
            status=status,
            root=tmp_path,
        ),
    )
    monkeypatch.setattr(
        webhooks_router,
        "delete_webhook",
        lambda webhook_id: service_delete_webhook(webhook_id=webhook_id, root=tmp_path),
    )

    create_response = client.post(
        "/v1/webhooks",
        json={
            "name": "Primary Webhook",
            "target_url": "https://example.com/webhook",
            "secret": "supersecret",
            "event_types": ["audit.completed", "regulatory.alert"],
        },
    )
    assert create_response.status_code == 200
    webhook_id = create_response.json()["data"]["webhook_id"]

    list_response = client.get("/v1/webhooks")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 1

    get_response = client.get(f"/v1/webhooks/{webhook_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["webhook_id"] == webhook_id

    queue_response = client.post(
        "/v1/webhooks/queue",
        json={
            "event_type": "audit.completed",
            "payload": {"run_id": "run_001", "overall_posture": "GREEN"},
        },
    )
    assert queue_response.status_code == 200
    assert queue_response.json()["data"]["delivery_count"] >= 1
    delivery_id = queue_response.json()["data"]["deliveries"][0]["delivery_id"]

    dispatch_response = client.post(f"/v1/webhooks/deliveries/{delivery_id}/dispatch")
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()["data"]["status"] == "SENT"

    deliveries_response = client.get("/v1/webhooks/deliveries")
    assert deliveries_response.status_code == 200
    assert deliveries_response.json()["data"]["count"] >= 1

    delivery_get = client.get(f"/v1/webhooks/deliveries/{delivery_id}")
    assert delivery_get.status_code == 200
    assert delivery_get.json()["data"]["delivery_id"] == delivery_id

    test_response = client.post(f"/v1/webhooks/{webhook_id}/test")
    assert test_response.status_code == 200
    assert test_response.json()["data"]["status"] == "SENT"

    update_response = client.patch(
        f"/v1/webhooks/{webhook_id}",
        json={"name": "Updated Webhook"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Updated Webhook"

    delete_response = client.delete(f"/v1/webhooks/{webhook_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
