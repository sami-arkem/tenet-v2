from __future__ import annotations

from datetime import date, timedelta

from core.audit_schedule_policy import (
    AuditSchedulePolicy,
    DueExecutionAction,
    REMINDER_LEAD_DAYS,
    STALE_EVIDENCE_DAYS,
    ScheduleFrequency,
    SkipReason,
    evaluate_due_execution,
    evaluate_reminder,
    materialize_due_executions,
)


def test_monthly_due_materializes_when_due_and_evidence_fresh() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-001",
        tenant_id="tenant-a",
        audit_kind="aml_periodic",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    decision = evaluate_due_execution(policy, date(2026, 2, 15))
    assert decision.action == DueExecutionAction.MATERIALIZE
    assert decision.skip_reason is None
    assert decision.due_date == "2026-02-15"
    assert decision.stale_evidence is False


def test_monthly_not_due_skips_with_not_due_reason() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-002",
        tenant_id="tenant-a",
        audit_kind="kyc_periodic",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    decision = evaluate_due_execution(policy, date(2026, 2, 14))
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.NOT_DUE
    assert decision.due_date == "2026-02-15"


def test_manual_schedule_never_materializes() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-003",
        tenant_id="tenant-b",
        audit_kind="manual_review",
        frequency=ScheduleFrequency.MANUAL,
        effective_from="2026-01-01",
        last_evidence_refresh_at="2026-01-10",
    )
    decision = evaluate_due_execution(policy, date(2026, 3, 1))
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.MANUAL_SCHEDULE
    assert decision.due_date is None


def test_stale_evidence_blocks_due_execution_beyond_sixty_days() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-004",
        tenant_id="tenant-c",
        audit_kind="sanctions_screening_review",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-02-15",
        last_evidence_refresh_at="2026-01-01",
    )
    # Policy is due 2026-03-15 (1 month after Feb 15)
    # Test date: March 15, 2026 - policy is due today
    # Evidence age: Jan 1 to Mar 15 = 73 days (> 60, stale)
    test_date = date(2026, 3, 15)
    decision = evaluate_due_execution(policy, test_date)
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.STALE_EVIDENCE
    assert decision.stale_evidence is True


def test_quarterly_and_biannual_due_dates_are_deterministic() -> None:
    quarterly = AuditSchedulePolicy(
        schedule_id="sched-q",
        tenant_id="tenant-q",
        audit_kind="quarterly_governance",
        frequency=ScheduleFrequency.QUARTERLY,
        effective_from="2026-01-31",
        last_run_at="2026-01-31",
        last_evidence_refresh_at="2026-03-01",
    )
    biannual = AuditSchedulePolicy(
        schedule_id="sched-b",
        tenant_id="tenant-b",
        audit_kind="biannual_vendor_risk",
        frequency=ScheduleFrequency.BIANNUAL,
        effective_from="2026-01-31",
        last_run_at="2026-01-31",
        last_evidence_refresh_at="2026-06-01",
    )
    assert quarterly.next_due_date(date(2026, 2, 1)).isoformat() == "2026-04-30"
    assert biannual.next_due_date(date(2026, 2, 1)).isoformat() == "2026-07-31"


def test_annual_due_date_is_deterministic() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-annual",
        tenant_id="tenant-y",
        audit_kind="annual_license_review",
        frequency=ScheduleFrequency.ANNUAL,
        effective_from="2026-02-28",
        last_run_at="2026-02-28",
        last_evidence_refresh_at="2027-01-15",
    )
    assert policy.next_due_date(date(2026, 12, 1)).isoformat() == "2027-02-28"


def test_custom_interval_due_date_is_supported() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-custom",
        tenant_id="tenant-z",
        audit_kind="custom_periodic",
        frequency=ScheduleFrequency.CUSTOM,
        effective_from="2026-01-01",
        custom_interval_days=45,
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-02-10",
    )
    assert policy.next_due_date(date(2026, 1, 2)).isoformat() == "2026-02-15"


def test_reminder_fires_inside_seven_day_window() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-reminder",
        tenant_id="tenant-r",
        audit_kind="monthly_reminder",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    reminder = evaluate_reminder(policy, date(2026, 2, 15 - REMINDER_LEAD_DAYS))
    assert reminder.should_remind is True
    assert reminder.reminder_for_date == "2026-02-15"


def test_disabled_schedule_skips_deterministically() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-disabled",
        tenant_id="tenant-d",
        audit_kind="disabled_audit",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        enabled=False,
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-20",
    )
    decision = evaluate_due_execution(policy, date(2026, 2, 1))
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.SCHEDULE_DISABLED


def test_invalid_custom_configuration_skips_as_invalid_configuration() -> None:
    # Policy with custom_interval_days on non-CUSTOM frequency is invalid
    policy = AuditSchedulePolicy(
        schedule_id="sched-invalid",
        tenant_id="tenant-i",
        audit_kind="bad_custom",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        custom_interval_days=30,  # Invalid: only allowed for CUSTOM frequency
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-02",
    )
    decision = evaluate_due_execution(policy, date(2026, 2, 1))
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.INVALID_CONFIGURATION


def test_due_execution_batch_sorts_materialized_and_skipped_deterministically() -> None:
    materialize = AuditSchedulePolicy(
        schedule_id="b",
        tenant_id="tenant-1",
        audit_kind="aml",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-20",
    )
    skip = AuditSchedulePolicy(
        schedule_id="a",
        tenant_id="tenant-1",
        audit_kind="kyc",
        frequency=ScheduleFrequency.MANUAL,
        effective_from="2026-01-01",
        last_evidence_refresh_at="2026-01-20",
    )
    batch = materialize_due_executions([materialize, skip], date(2026, 2, 1))
    assert [x.schedule_id for x in batch.materialized] == ["b"]
    assert [x.schedule_id for x in batch.skipped] == ["a"]


def test_missing_evidence_refresh_is_treated_as_stale() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-no-evidence",
        tenant_id="tenant-n",
        audit_kind="aml_missing_evidence",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        last_run_at="2026-01-01",
        last_evidence_refresh_at=None,
    )
    decision = evaluate_due_execution(policy, date(2026, 2, 1))
    assert decision.action == DueExecutionAction.SKIP
    assert decision.skip_reason == SkipReason.STALE_EVIDENCE
