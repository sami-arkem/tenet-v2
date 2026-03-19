from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_notifications_api_flow(tmp_path, monkeypatch):
    from api.routers import notifications as notifications_router
    from core.notification_outbox_service import (
        dispatch_notification as service_dispatch_notification,
        get_notification as service_get_notification,
        list_notifications as service_list_notifications,
        queue_notification_event as service_queue_notification_event,
    )

    monkeypatch.setattr(
        notifications_router,
        "queue_notification_event",
        lambda event_type, payload, recipients, channels=None: service_queue_notification_event(
            event_type=event_type,
            payload=payload,
            recipients=recipients,
            channels=channels,
            root=tmp_path,
        ),
    )
    monkeypatch.setattr(
        notifications_router,
        "dispatch_notification",
        lambda notification_id: service_dispatch_notification(notification_id=notification_id, root=tmp_path),
    )
    monkeypatch.setattr(
        notifications_router,
        "get_notification",
        lambda notification_id: service_get_notification(notification_id=notification_id, root=tmp_path),
    )
    monkeypatch.setattr(
        notifications_router,
        "list_notifications",
        lambda: service_list_notifications(root=tmp_path),
    )

    queue_response = client.post(
        "/v1/notifications/queue",
        json={
            "event_type": "AUDIT_COMPLETE",
            "payload": {
                "run_id": "run_001",
                "overall_posture": "GREEN",
                "deployment_decision": "APPROVED",
            },
            "recipients": [
                {
                    "user_id": "user_001",
                    "email": "owner@example.com",
                    "notification_preferences": {
                        "audit_complete": {"email": True, "in_app": True},
                        "finding_assigned": {"email": True, "in_app": True},
                        "finding_overdue": {"email": True, "in_app": True},
                        "regulatory_alert": {"email": True, "in_app": True},
                        "weekly_summary": {"email": False, "in_app": True},
                    },
                }
            ],
            "channels": ["email", "in_app"],
        },
    )
    assert queue_response.status_code == 200
    notification_id = queue_response.json()["data"]["notification_id"]

    dispatch_response = client.post(f"/v1/notifications/{notification_id}/dispatch")
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()["data"]["status"] == "SENT"

    get_response = client.get(f"/v1/notifications/{notification_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["notification_id"] == notification_id

    list_response = client.get("/v1/notifications")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 1


def test_notifications_regulatory_alert_api_flow(tmp_path, monkeypatch):
    from api.routers import notifications as notifications_router
    from core.notification_outbox_service import queue_regulatory_alert_notification as service_queue_regulatory_alert_notification

    monkeypatch.setattr(
        notifications_router,
        "queue_regulatory_alert_notification",
        lambda alert_payload, recipients: service_queue_regulatory_alert_notification(
            alert_payload=alert_payload,
            recipients=recipients,
            root=tmp_path,
        ),
    )

    queue_response = client.post(
        "/v1/notifications/queue/regulatory-alert",
        json={
            "alert_payload": {
                "title": "FATF update",
                "summary": "Global AML standard update",
                "controls_to_review": ["AML-01", "AML-04"],
                "jurisdictions": ["global"],
            },
            "recipients": [
                {
                    "user_id": "user_002",
                    "email": "admin@example.com",
                    "notification_preferences": {
                        "audit_complete": {"email": True, "in_app": True},
                        "finding_assigned": {"email": True, "in_app": True},
                        "finding_overdue": {"email": True, "in_app": True},
                        "regulatory_alert": {"email": True, "in_app": True},
                        "weekly_summary": {"email": False, "in_app": True},
                    },
                }
            ],
        },
    )
    assert queue_response.status_code == 200
    assert queue_response.json()["data"]["event_type"] == "REGULATORY_ALERT_HIGH"
