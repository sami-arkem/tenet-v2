from __future__ import annotations

import json
from pathlib import Path

from core.audit_schedule_delivery import (
    DeliveryState,
    append_delivery_outputs,
    build_delivery_artifacts,
    load_delivery_state,
    save_delivery_state,
    write_readiness_snapshot,
)


def _runtime_cycle_payload() -> dict:
    return {
        "schema_version": "1.0",
        "cycle_date": "2026-02-15",
        "executions": [
            {
                "execution_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
                "schedule_id": "sched-001",
                "tenant_id": "tenant-a",
                "audit_kind": "aml_periodic",
                "due_date": "2026-02-15",
                "execution_date": "2026-02-15",
                "execution_key": "tenant-a:aml_periodic:sched-001:2026-02-15",
                "source_policy_hash": "abc",
            }
        ],
        "reminder_events": [
            {
                "event_id": "tenant-a:aml_periodic:sched-001:AUDIT_REMINDER:2026-02-15",
                "schedule_id": "sched-001",
                "tenant_id": "tenant-a",
                "audit_kind": "aml_periodic",
                "event_kind": "AUDIT_REMINDER",
                "target_date": "2026-02-15",
                "payload_hash": "r1",
            }
        ],
        "skip_events": [
            {
                "event_id": "tenant-b:sanctions_review:sched-002:SCHEDULE_STALE_EVIDENCE:2026-02-01",
                "schedule_id": "sched-002",
                "tenant_id": "tenant-b",
                "audit_kind": "sanctions_review",
                "event_kind": "SCHEDULE_STALE_EVIDENCE",
                "target_date": "2026-02-01",
                "payload_hash": "s1",
            }
        ],
        "skipped": [
            {
                "schedule_id": "sched-002",
                "tenant_id": "tenant-b",
                "audit_kind": "sanctions_review",
                "due_date": "2026-02-01",
                "skip_reason": "STALE_EVIDENCE",
                "stale_evidence": True,
            },
            {
                "schedule_id": "sched-003",
                "tenant_id": "tenant-c",
                "audit_kind": "manual_review",
                "due_date": None,
                "skip_reason": "MANUAL_SCHEDULE",
                "stale_evidence": False,
            },
            {
                "schedule_id": "sched-004",
                "tenant_id": "tenant-d",
                "audit_kind": "disabled_review",
                "due_date": "2026-02-01",
                "skip_reason": "SCHEDULE_DISABLED",
                "stale_evidence": False,
            },
            {
                "schedule_id": "sched-005",
                "tenant_id": "tenant-e",
                "audit_kind": "bad_custom",
                "due_date": "2026-02-01",
                "skip_reason": "INVALID_CONFIGURATION",
                "stale_evidence": False,
            },
        ],
    }


def test_build_delivery_artifacts_creates_queue_outbox_alerts_and_snapshot() -> None:
    result, next_state = build_delivery_artifacts(_runtime_cycle_payload())

    assert len(result.queue_entries) == 1
    assert result.queue_entries[0].queue_id == "tenant-a:aml_periodic:sched-001:2026-02-15"

    assert len(result.outbox_entries) == 2
    assert {x.event_kind for x in result.outbox_entries} == {
        "AUDIT_REMINDER",
        "SCHEDULE_STALE_EVIDENCE",
    }

    assert len(result.readiness_alerts) == 3
    reasons = {x.reason for x in result.readiness_alerts}
    assert reasons == {"STALE_EVIDENCE", "SCHEDULE_DISABLED", "INVALID_CONFIGURATION"}

    assert result.readiness_snapshot is not None
    assert result.readiness_snapshot.readiness_blocked is True
    assert result.readiness_snapshot.total_executions == 1
    assert result.readiness_snapshot.total_notifications == 2
    assert result.readiness_snapshot.total_alerts == 3
    assert sorted(result.readiness_snapshot.blocking_reasons) == [
        "invalid_configuration:1",
        "schedule_disabled:1",
        "stale_evidence:1",
    ]

    assert "tenant-a:aml_periodic:sched-001:2026-02-15" in next_state.emitted_queue_ids


def test_delivery_deduplicates_using_state() -> None:
    state = DeliveryState(
        emitted_queue_ids=["tenant-a:aml_periodic:sched-001:2026-02-15"],
        emitted_outbox_ids=[
            "tenant-a:aml_periodic:sched-001:AUDIT_REMINDER:2026-02-15",
            "tenant-b:sanctions_review:sched-002:SCHEDULE_STALE_EVIDENCE:2026-02-01",
        ],
        emitted_alert_ids=[
            "tenant-b:sanctions_review:sched-002:STALE_EVIDENCE:2026-02-01",
            "tenant-d:disabled_review:sched-004:SCHEDULE_DISABLED:2026-02-01",
            "tenant-e:bad_custom:sched-005:INVALID_CONFIGURATION:2026-02-01",
        ],
    )

    result, _ = build_delivery_artifacts(_runtime_cycle_payload(), state=state)

    assert result.queue_entries == []
    assert result.outbox_entries == []
    assert result.readiness_alerts == []
    assert result.readiness_snapshot is not None
    assert result.readiness_snapshot.total_executions == 0
    assert result.readiness_snapshot.total_notifications == 0
    assert result.readiness_snapshot.total_alerts == 0


def test_append_delivery_outputs_writes_jsonl_without_duplicates(tmp_path: Path) -> None:
    result, _ = build_delivery_artifacts(_runtime_cycle_payload())

    queue_path = tmp_path / "queue.jsonl"
    outbox_path = tmp_path / "outbox.jsonl"
    alerts_path = tmp_path / "alerts.jsonl"

    append_delivery_outputs(
        result=result,
        queue_path=queue_path,
        outbox_path=outbox_path,
        alerts_path=alerts_path,
    )
    append_delivery_outputs(
        result=result,
        queue_path=queue_path,
        outbox_path=outbox_path,
        alerts_path=alerts_path,
    )

    queue_rows = [json.loads(x) for x in queue_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    outbox_rows = [json.loads(x) for x in outbox_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    alert_rows = [json.loads(x) for x in alerts_path.read_text(encoding="utf-8").splitlines() if x.strip()]

    assert len(queue_rows) == 1
    assert len(outbox_rows) == 2
    assert len(alert_rows) == 3


def test_delivery_state_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "delivery_state.json"
    original = DeliveryState(
        emitted_queue_ids=["q2", "q1"],
        emitted_outbox_ids=["o2", "o1"],
        emitted_alert_ids=["a2", "a1"],
    )

    save_delivery_state(state_path, original)
    loaded = load_delivery_state(state_path)

    assert loaded.emitted_queue_ids == ["q1", "q2"]
    assert loaded.emitted_outbox_ids == ["o1", "o2"]
    assert loaded.emitted_alert_ids == ["a1", "a2"]


def test_snapshot_write_persists_json(tmp_path: Path) -> None:
    result, _ = build_delivery_artifacts(_runtime_cycle_payload())
    snapshot_path = tmp_path / "readiness_snapshot.json"

    assert result.readiness_snapshot is not None
    write_readiness_snapshot(snapshot_path, result.readiness_snapshot)

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["readiness_blocked"] is True
    assert payload["stale_evidence_alerts"] == 1
    assert payload["invalid_configuration_alerts"] == 1
    assert payload["schedule_disabled_alerts"] == 1


def test_manual_schedule_skip_does_not_become_readiness_alert() -> None:
    payload = _runtime_cycle_payload()
    payload["skipped"] = [
        {
            "schedule_id": "sched-003",
            "tenant_id": "tenant-c",
            "audit_kind": "manual_review",
            "due_date": None,
            "skip_reason": "MANUAL_SCHEDULE",
            "stale_evidence": False,
        }
    ]
    payload["executions"] = []
    payload["reminder_events"] = []
    payload["skip_events"] = []

    result, _ = build_delivery_artifacts(payload)

    assert result.readiness_alerts == []
    assert result.readiness_snapshot is not None
    assert result.readiness_snapshot.readiness_blocked is False
    assert result.readiness_snapshot.blocking_reasons == []
