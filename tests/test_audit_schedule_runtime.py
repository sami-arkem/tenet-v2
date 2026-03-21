from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from core.audit_schedule_policy import AuditSchedulePolicy, ScheduleFrequency
from core.audit_schedule_runtime import (
    RuntimeState,
    load_runtime_state,
    run_schedule_cycle,
    save_runtime_state,
    write_cycle_artifacts,
)


def test_materializes_due_execution_once_and_persists_dedup_state(tmp_path: Path) -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-001",
        tenant_id="tenant-a",
        audit_kind="aml_periodic",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    first_result, first_state = run_schedule_cycle([policy], cycle_date=date(2026, 2, 15))
    second_result, second_state = run_schedule_cycle([policy], cycle_date=date(2026, 2, 15), state=first_state)
    assert len(first_result.executions) == 1
    assert first_result.executions[0].execution_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert len(second_result.executions) == 0
    assert second_state.materialized_execution_keys == first_state.materialized_execution_keys


def test_emits_reminder_once_inside_window() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-002",
        tenant_id="tenant-a",
        audit_kind="kyc_periodic",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    first_result, first_state = run_schedule_cycle([policy], cycle_date=date(2026, 2, 8))
    second_result, _ = run_schedule_cycle([policy], cycle_date=date(2026, 2, 8), state=first_state)
    assert len(first_result.reminder_events) == 1
    assert first_result.reminder_events[0].event_kind == "AUDIT_REMINDER"
    assert first_result.reminder_events[0].target_date == "2026-02-15"
    assert len(second_result.reminder_events) == 0


def test_stale_evidence_produces_skip_record_and_notification() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-003",
        tenant_id="tenant-b",
        audit_kind="sanctions_review",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2025-11-01",
    )
    result, _ = run_schedule_cycle([policy], cycle_date=date(2026, 2, 1))
    assert len(result.executions) == 0
    assert len(result.skipped) == 1
    assert result.skipped[0].skip_reason == "STALE_EVIDENCE"
    assert len(result.skip_events) == 1
    assert result.skip_events[0].event_kind == "SCHEDULE_STALE_EVIDENCE"


def test_invalid_configuration_produces_skip_notification() -> None:
    # Policy with custom_interval_days on non-CUSTOM frequency is invalid
    policy = AuditSchedulePolicy(
        schedule_id="sched-004",
        tenant_id="tenant-c",
        audit_kind="custom_bad",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        custom_interval_days=30,  # Invalid: only allowed for CUSTOM frequency
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-05",
    )
    result, _ = run_schedule_cycle([policy], cycle_date=date(2026, 2, 1))
    assert len(result.executions) == 0
    assert len(result.skipped) == 1
    assert result.skipped[0].skip_reason == "INVALID_CONFIGURATION"
    assert len(result.skip_events) == 1
    assert result.skip_events[0].event_kind == "SCHEDULE_INVALID_CONFIGURATION"


def test_manual_schedule_skips_without_spurious_skip_notification() -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-005",
        tenant_id="tenant-d",
        audit_kind="manual_governance",
        frequency=ScheduleFrequency.MANUAL,
        effective_from="2026-01-01",
        last_evidence_refresh_at="2026-01-10",
    )
    result, _ = run_schedule_cycle([policy], cycle_date=date(2026, 2, 1))
    assert len(result.executions) == 0
    assert len(result.skipped) == 1
    assert result.skipped[0].skip_reason == "MANUAL_SCHEDULE"
    assert result.skip_events == []


def test_runtime_outputs_are_deterministically_sorted() -> None:
    a = AuditSchedulePolicy(
        schedule_id="z",
        tenant_id="tenant-2",
        audit_kind="kyc",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-20",
    )
    b = AuditSchedulePolicy(
        schedule_id="a",
        tenant_id="tenant-1",
        audit_kind="aml",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-01",
        last_run_at="2026-01-01",
        last_evidence_refresh_at="2026-01-20",
    )
    result, _ = run_schedule_cycle([a, b], cycle_date=date(2026, 2, 1))
    assert [x.schedule_id for x in result.executions] == ["a", "z"]


def test_state_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "runtime_state.json"
    original = RuntimeState(
        materialized_execution_keys=["k2", "k1"],
        emitted_notification_keys=["n2", "n1"],
    )
    save_runtime_state(state_path, original)
    loaded = load_runtime_state(state_path)
    assert loaded.materialized_execution_keys == ["k1", "k2"]
    assert loaded.emitted_notification_keys == ["n1", "n2"]


def test_cycle_artifacts_are_written(tmp_path: Path) -> None:
    policy = AuditSchedulePolicy(
        schedule_id="sched-006",
        tenant_id="tenant-e",
        audit_kind="aml_periodic",
        frequency=ScheduleFrequency.MONTHLY,
        effective_from="2026-01-15",
        last_run_at="2026-01-15",
        last_evidence_refresh_at="2026-02-10",
    )
    result, state = run_schedule_cycle([policy], cycle_date=date(2026, 2, 15))
    output_path = tmp_path / "runtime_cycle.json"
    state_path = tmp_path / "runtime_state.json"
    write_cycle_artifacts(
        output_path=output_path,
        state_path=state_path,
        result=result,
        state=state,
    )
    output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert output_payload["schema_version"] == "1.0"
    assert output_payload["executions"][0]["schedule_id"] == "sched-006"
    assert state_payload["materialized_execution_keys"] == [
        "tenant-e:aml_periodic:sched-006:2026-02-15"
    ]
