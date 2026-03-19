from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.schedule_service import (
    STATUS_ACTIVE,
    STATUS_PAUSED,
    build_due_schedule_run_plan,
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    mark_schedule_run_executed,
    update_schedule,
)


def test_create_get_list_update_delete_schedule(tmp_path: Path):
    created = create_schedule(
        tenant_id="tenant_001",
        name="Weekly AML Audit",
        frequency="WEEKLY",
        starts_at="2026-03-18T06:00:00+00:00",
        timezone="Europe/London",
        audit_payload={"audit_type": "aml_readiness_review"},
        weekdays=["WE"],
        root=tmp_path,
    )
    assert created["status"] == STATUS_ACTIVE
    assert created["schedule_id"].startswith("sch_")

    loaded = get_schedule(schedule_id=created["schedule_id"], root=tmp_path)
    assert loaded["schedule_id"] == created["schedule_id"]

    listed = list_schedules(tmp_path)
    assert listed["count"] == 1

    updated = update_schedule(
        schedule_id=created["schedule_id"],
        name="Weekly AML Audit Updated",
        status=STATUS_PAUSED,
        root=tmp_path,
    )
    assert updated["name"] == "Weekly AML Audit Updated"
    assert updated["status"] == STATUS_PAUSED
    assert updated["next_run_at"] is None

    deleted = delete_schedule(schedule_id=created["schedule_id"], root=tmp_path)
    assert deleted["deleted"] is True


def test_due_plan_and_mark_executed(tmp_path: Path):
    created = create_schedule(
        tenant_id="tenant_001",
        name="Daily Audit",
        frequency="DAILY",
        starts_at="2026-03-17T06:00:00+00:00",
        timezone="UTC",
        audit_payload={"audit_type": "aml_readiness_review"},
        root=tmp_path,
    )

    plan = build_due_schedule_run_plan(
        as_of=datetime(2026, 3, 19, 7, 0, tzinfo=timezone.utc),
        limit=10,
        root=tmp_path,
    )
    assert plan["candidate_count"] >= 1
    assert plan["items"][0]["schedule_id"] == created["schedule_id"]

    executed = mark_schedule_run_executed(
        schedule_id=created["schedule_id"],
        executed_at="2026-03-19T07:00:00+00:00",
        root=tmp_path,
    )
    assert executed["last_run_at"] == "2026-03-19T07:00:00+00:00"
    assert executed["next_run_at"] is not None
