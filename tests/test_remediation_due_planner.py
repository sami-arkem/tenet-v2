from __future__ import annotations

from core.remediation_due_planner import plan_due_notifications


def _rows() -> list[dict]:
    return [
        {
            "remediation_id": "r1",
            "audit_id": "a1",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "status": "OPEN",
            "owner_user_id": "user-1",
            "due_date": "2026-03-25",
        },
        {
            "remediation_id": "r2",
            "audit_id": "a2",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "status": "IN_PROGRESS",
            "owner_user_id": "user-2",
            "due_date": "2026-03-10",
        },
        {
            "remediation_id": "r3",
            "audit_id": "a3",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "status": "CLOSED",
            "owner_user_id": "user-3",
            "due_date": "2026-03-18",
        },
    ]


def test_due_planner_creates_due_soon_and_overdue_and_dedupes() -> None:
    planned = plan_due_notifications(
        lifecycle_items=_rows(),
        existing_outbox=[],
        today="2026-03-19",
        now="2026-03-19T09:00:00Z",
    )

    assert len(planned) == 2
    event_types = sorted([row["event_type"] for row in planned])
    assert event_types == ["REMEDIATION_DUE_SOON", "REMEDIATION_OVERDUE"]

    planned_again = plan_due_notifications(
        lifecycle_items=_rows(),
        existing_outbox=planned,
        today="2026-03-19",
        now="2026-03-19T10:00:00Z",
    )
    assert len(planned_again) == 2
