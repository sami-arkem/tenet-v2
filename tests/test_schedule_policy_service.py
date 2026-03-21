from __future__ import annotations

from datetime import date
from pathlib import Path

from core.schedule_policy_service import (
    DEFAULT_NOTIFY_BEFORE_DAYS,
    FREQ_ANNUAL,
    FREQ_BIANNUAL,
    FREQ_CUSTOM,
    FREQ_MANUAL,
    FREQ_MONTHLY,
    FREQ_QUARTERLY,
    SKIP_INACTIVE,
    SKIP_MANUAL_ONLY,
    SKIP_MISSING_EVIDENCE_TIMESTAMP,
    SKIP_NOT_DUE,
    SKIP_STALE_EVIDENCE,
    build_due_execution_plan,
    build_schedule_reminder_plan,
    create_policy_schedule,
    delete_policy_schedule,
    evaluate_schedule_auto_run_eligibility,
    get_policy_schedule,
    list_policy_schedules,
    mark_policy_schedule_executed,
    update_policy_schedule,
)


def _audit_payload(latest_evidence_at: str | None) -> dict:
    payload = {
        "audit_type": "aml_readiness_review",
        "regime_scope": ["AML"],
        "jurisdiction": "UK",
    }
    if latest_evidence_at is not None:
        payload["latest_evidence_at"] = latest_evidence_at
    return payload


def test_create_get_list_update_delete_policy_schedule(tmp_path: Path):
    created = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Quarterly AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_QUARTERLY,
        next_run_date="2026-03-25",
        audit_payload=_audit_payload("2026-03-15T00:00:00+00:00"),
        notify_users=["user_001"],
        root=tmp_path,
    )
    assert created["frequency"] == FREQ_QUARTERLY
    assert created["notify_before_days"] == DEFAULT_NOTIFY_BEFORE_DAYS

    loaded = get_policy_schedule(schedule_id=created["schedule_id"], root=tmp_path)
    assert loaded["schedule_id"] == created["schedule_id"]

    listed = list_policy_schedules(root=tmp_path)
    assert listed["count"] == 1

    updated = update_policy_schedule(
        schedule_id=created["schedule_id"],
        root=tmp_path,
        status="PAUSED",
        is_active=False,
    )
    assert updated["status"] == "PAUSED"
    assert updated["is_active"] is False

    deleted = delete_policy_schedule(schedule_id=created["schedule_id"], root=tmp_path)
    assert deleted["deleted"] is True


def test_reminder_plan_matches_bible_default(tmp_path: Path):
    create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Monthly AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-25",
        audit_payload=_audit_payload("2026-03-15T00:00:00+00:00"),
        notify_users=["user_001", "user_002"],
        root=tmp_path,
    )

    reminders = build_schedule_reminder_plan(
        as_of_date=date(2026, 3, 18),
        root=tmp_path,
    )
    assert reminders["count"] == 1
    assert reminders["items"][0]["notify_before_days"] == 7
    assert "due in 7 days" in reminders["items"][0]["message"]


def test_eligibility_blocks_manual_inactive_not_due_and_stale(tmp_path: Path):
    manual = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Manual AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MANUAL,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-15T00:00:00+00:00"),
        root=tmp_path,
    )
    manual_eval = evaluate_schedule_auto_run_eligibility(schedule=manual, as_of_date=date(2026, 3, 18))
    assert manual_eval["eligible"] is False
    assert SKIP_MANUAL_ONLY in manual_eval["skip_reasons"]

    inactive = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Inactive AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-15T00:00:00+00:00"),
        root=tmp_path,
    )
    inactive = update_policy_schedule(
        schedule_id=inactive["schedule_id"],
        root=tmp_path,
        status="PAUSED",
        is_active=False,
    )
    inactive_eval = evaluate_schedule_auto_run_eligibility(schedule=inactive, as_of_date=date(2026, 3, 18))
    assert SKIP_INACTIVE in inactive_eval["skip_reasons"]

    not_due = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Not Due AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-20",
        audit_payload=_audit_payload("2026-03-15T00:00:00+00:00"),
        root=tmp_path,
    )
    not_due_eval = evaluate_schedule_auto_run_eligibility(schedule=not_due, as_of_date=date(2026, 3, 18))
    assert SKIP_NOT_DUE in not_due_eval["skip_reasons"]

    stale = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Stale AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-01-01T00:00:00+00:00"),
        root=tmp_path,
    )
    stale_eval = evaluate_schedule_auto_run_eligibility(schedule=stale, as_of_date=date(2026, 3, 18))
    assert stale_eval["eligible"] is False
    assert SKIP_STALE_EVIDENCE in stale_eval["skip_reasons"]

    missing_ts = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Missing Timestamp AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload(None),
        root=tmp_path,
    )
    missing_eval = evaluate_schedule_auto_run_eligibility(schedule=missing_ts, as_of_date=date(2026, 3, 18))
    assert SKIP_MISSING_EVIDENCE_TIMESTAMP in missing_eval["skip_reasons"]


def test_due_execution_plan_materializes_only_eligible_runs(tmp_path: Path):
    eligible = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Eligible AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-01T00:00:00+00:00"),
        entity_id="entity_001",
        root=tmp_path,
    )
    create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Blocked AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2025-12-31T00:00:00+00:00"),
        root=tmp_path,
    )

    plan = build_due_execution_plan(
        as_of_date=date(2026, 3, 18),
        limit=10,
        root=tmp_path,
    )
    assert plan["eligible_count"] == 1
    assert plan["scheduled_count"] == 1
    assert plan["eligible_items"][0]["schedule_id"] == eligible["schedule_id"]
    assert plan["eligible_items"][0]["audit_run_request"]["trigger_type"] == "SCHEDULED_AUTO_RUN"
    assert plan["skipped_count"] == 1
    assert SKIP_STALE_EVIDENCE in plan["skipped_items"][0]["skip_reasons"]


def test_mark_executed_advances_frequency_per_bible_spec(tmp_path: Path):
    monthly = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Monthly AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_MONTHLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-10T00:00:00+00:00"),
        root=tmp_path,
    )
    quarterly = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Quarterly AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_QUARTERLY,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-10T00:00:00+00:00"),
        root=tmp_path,
    )
    biannual = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Biannual AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_BIANNUAL,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-10T00:00:00+00:00"),
        root=tmp_path,
    )
    annual = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Annual AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_ANNUAL,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-10T00:00:00+00:00"),
        root=tmp_path,
    )
    custom = create_policy_schedule(
        tenant_id="tenant_001",
        created_by="user_001",
        name="Custom AML Audit",
        regime_scope=["AML"],
        jurisdiction="UK",
        frequency=FREQ_CUSTOM,
        custom_interval_days=45,
        next_run_date="2026-03-18",
        audit_payload=_audit_payload("2026-03-10T00:00:00+00:00"),
        root=tmp_path,
    )

    monthly = mark_policy_schedule_executed(
        schedule_id=monthly["schedule_id"],
        last_run_id="TEN-20260318-aaaa1111",
        executed_at="2026-03-18T08:00:00+00:00",
        root=tmp_path,
    )
    quarterly = mark_policy_schedule_executed(
        schedule_id=quarterly["schedule_id"],
        last_run_id="TEN-20260318-bbbb2222",
        executed_at="2026-03-18T08:00:00+00:00",
        root=tmp_path,
    )
    biannual = mark_policy_schedule_executed(
        schedule_id=biannual["schedule_id"],
        last_run_id="TEN-20260318-cccc3333",
        executed_at="2026-03-18T08:00:00+00:00",
        root=tmp_path,
    )
    annual = mark_policy_schedule_executed(
        schedule_id=annual["schedule_id"],
        last_run_id="TEN-20260318-dddd4444",
        executed_at="2026-03-18T08:00:00+00:00",
        root=tmp_path,
    )
    custom = mark_policy_schedule_executed(
        schedule_id=custom["schedule_id"],
        last_run_id="TEN-20260318-eeee5555",
        executed_at="2026-03-18T08:00:00+00:00",
        root=tmp_path,
    )

    assert monthly["next_run_date"] == "2026-04-18"
    assert quarterly["next_run_date"] == "2026-06-18"
    assert biannual["next_run_date"] == "2026-09-18"
    assert annual["next_run_date"] == "2027-03-18"
    assert custom["next_run_date"] == "2026-05-02"
