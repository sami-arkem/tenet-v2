from __future__ import annotations

from pathlib import Path

from core.notification_outbox_service import (
    EVENT_AUDIT_COMPLETE,
    dispatch_notification,
    get_notification,
    list_notifications,
    queue_notification_event,
    queue_regulatory_alert_notification,
)


def test_queue_and_dispatch_notification(tmp_path: Path):
    notif = queue_notification_event(
        event_type=EVENT_AUDIT_COMPLETE,
        payload={
            "run_id": "run_001",
            "overall_posture": "GREEN",
            "deployment_decision": "APPROVED",
        },
        recipients=[
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
        root=tmp_path,
    )
    assert notif["event_type"] == EVENT_AUDIT_COMPLETE
    assert notif["status"] == "QUEUED"
    assert len(notif["deliveries"]) == 2

    dispatched = dispatch_notification(notification_id=notif["notification_id"], root=tmp_path)
    assert dispatched["status"] == "SENT"
    assert dispatched["sent_count"] == 2
    assert dispatched["failed_count"] == 0
    assert dispatched["skipped_count"] == 0

    loaded = get_notification(notif["notification_id"], root=tmp_path)
    assert loaded["status"] == "SENT"


def test_regulatory_alert_preferences_respected(tmp_path: Path):
    notif = queue_regulatory_alert_notification(
        alert_payload={
            "title": "FCA update",
            "summary": "Important change",
            "controls_to_review": ["AML-04"],
            "jurisdictions": ["uk"],
        },
        recipients=[
            {
                "user_id": "user_001",
                "email": "admin@example.com",
                "notification_preferences": {
                    "audit_complete": {"email": True, "in_app": True},
                    "finding_assigned": {"email": True, "in_app": True},
                    "finding_overdue": {"email": True, "in_app": True},
                    "regulatory_alert": {"email": False, "in_app": True},
                    "weekly_summary": {"email": False, "in_app": True},
                },
            }
        ],
        root=tmp_path,
    )

    assert len(notif["deliveries"]) == 2
    email_delivery = [item for item in notif["deliveries"] if item["channel"] == "email"][0]
    in_app_delivery = [item for item in notif["deliveries"] if item["channel"] == "in_app"][0]
    assert email_delivery["status"] == "SKIPPED"
    assert in_app_delivery["status"] == "QUEUED"

    dispatched = dispatch_notification(notification_id=notif["notification_id"], root=tmp_path)
    assert dispatched["sent_count"] == 1
    assert dispatched["skipped_count"] == 1

    listed = list_notifications(root=tmp_path)
    assert listed["count"] == 1
