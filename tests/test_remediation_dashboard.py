from __future__ import annotations

from core.remediation_dashboard import build_remediation_dashboard


def _rows() -> list[dict]:
    return [
        {
            "remediation_id": "r1",
            "audit_id": "a1",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "title": "Owner item",
            "severity": "HIGH",
            "status": "OPEN",
            "owner_user_id": "user-1",
            "due_date": "2026-03-25",
            "release_blocking": True,
            "closed_at": None,
        },
        {
            "remediation_id": "r2",
            "audit_id": "a2",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "title": "Overdue item",
            "severity": "CRITICAL",
            "status": "IN_PROGRESS",
            "owner_user_id": "user-2",
            "due_date": "2026-03-10",
            "release_blocking": True,
            "closed_at": None,
        },
        {
            "remediation_id": "r3",
            "audit_id": "a3",
            "tenant_id": "tenant-1",
            "audit_kind": "aml",
            "title": "Closed item",
            "severity": "LOW",
            "status": "CLOSED",
            "owner_user_id": "user-3",
            "due_date": "2026-03-18",
            "release_blocking": False,
            "closed_at": "2026-03-18T10:00:00Z",
        },
    ]


def test_dashboard_counts_and_sorting() -> None:
    dashboard = build_remediation_dashboard(
        lifecycle_items=_rows(),
        actor_user_id="user-1",
        tenant_id="tenant-1",
        today="2026-03-19",
    )

    assert dashboard.open_count == 1
    assert dashboard.in_progress_count == 1
    assert dashboard.overdue_count == 1
    assert dashboard.closed_this_month_count == 1

    assert dashboard.rows[0].remediation_id == "r1"
    assert dashboard.rows[0].sort_bucket == "ASSIGNED_TO_ME"
    assert dashboard.rows[1].remediation_id == "r2"
    assert dashboard.rows[1].sort_bucket == "OVERDUE"
