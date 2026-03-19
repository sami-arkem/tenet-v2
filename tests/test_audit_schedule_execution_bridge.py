from __future__ import annotations

import json
from pathlib import Path

from core.audit_schedule_execution_bridge import (
    ExecutionBridgeState,
    append_audit_creation_requests,
    build_execution_bridge_outputs,
    load_due_execution_queue,
    load_execution_bridge_state,
    load_readiness_alerts,
    load_readiness_snapshot,
    save_execution_bridge_state,
    write_schedule_gate,
)


def _queue_rows() -> list[dict]:
    return [
        {
            "audit_kind": "aml_periodic",
            "due_date": "2026-02-15",
            "execution_date": "2026-02-15",
            "payload_hash": "02b2",
            "queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "schedule_id": "sched-001",
            "source_execution_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "source_policy_hash": "abc123",
            "tenant_id": "tenant-a",
        },
        {
            "audit_kind": "vendor_risk_review",
            "due_date": "2026-02-20",
            "execution_date": "2026-02-20",
            "payload_hash": "91ab",
            "queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "schedule_id": "sched-010",
            "source_execution_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "source_policy_hash": "def456",
            "tenant_id": "tenant-b",
        },
    ]


def _alerts_rows() -> list[dict]:
    return [
        {
            "alert_id": "tenant-b:sanctions_review:sched-002:STALE_EVIDENCE:2026-02-01",
            "audit_kind": "sanctions_review",
            "due_date": "2026-02-01",
            "payload_hash": "6a5b",
            "reason": "STALE_EVIDENCE",
            "schedule_id": "sched-002",
            "severity": "HIGH",
            "tenant_id": "tenant-b",
        },
        {
            "alert_id": "tenant-d:disabled_review:sched-004:SCHEDULE_DISABLED:2026-02-01",
            "audit_kind": "disabled_review",
            "due_date": "2026-02-01",
            "payload_hash": "19c0",
            "reason": "SCHEDULE_DISABLED",
            "schedule_id": "sched-004",
            "severity": "MEDIUM",
            "tenant_id": "tenant-d",
        },
    ]


def _snapshot_payload() -> dict:
    return {
        "blocking_reasons": [
            "stale_evidence:1",
            "schedule_disabled:1",
        ],
        "cycle_date": "2026-02-15",
        "invalid_configuration_alerts": 0,
        "readiness_blocked": True,
        "schedule_disabled_alerts": 1,
        "schema_version": "1.0",
        "stale_evidence_alerts": 1,
        "total_alerts": 2,
        "total_executions": 2,
        "total_notifications": 2,
    }


def test_build_execution_bridge_outputs_creates_requests_and_gate() -> None:
    result, next_state = build_execution_bridge_outputs(
        due_execution_queue=_queue_rows(),
        readiness_snapshot=_snapshot_payload(),
        readiness_alerts=_alerts_rows(),
    )

    assert len(result.audit_creation_requests) == 2
    assert result.audit_creation_requests[0].request_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert result.audit_creation_requests[0].workflow_status == "PENDING_AUDIT_CREATION"
    assert result.audit_creation_requests[1].tenant_id == "tenant-b"

    assert result.schedule_gate is not None
    assert result.schedule_gate.gate_name == "audit_schedule_runtime_gate"
    assert result.schedule_gate.gate_status == "BLOCKED"
    assert result.schedule_gate.schedule_runtime_ready is False
    assert result.schedule_gate.total_due_execution_requests == 2
    assert result.schedule_gate.total_alerts == 2
    assert result.schedule_gate.blocking_alert_ids == sorted([
        "tenant-b:sanctions_review:sched-002:STALE_EVIDENCE:2026-02-01",
        "tenant-d:disabled_review:sched-004:SCHEDULE_DISABLED:2026-02-01",
    ])

    assert next_state.emitted_request_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_build_execution_bridge_outputs_deduplicates_requests_via_state() -> None:
    state = ExecutionBridgeState(
        emitted_request_ids=[
            "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant-b:vendor_risk_review:sched-010:2026-02-20",
        ]
    )

    result, next_state = build_execution_bridge_outputs(
        due_execution_queue=_queue_rows(),
        readiness_snapshot=_snapshot_payload(),
        readiness_alerts=_alerts_rows(),
        state=state,
    )

    assert result.audit_creation_requests == []
    assert result.schedule_gate is not None
    assert result.schedule_gate.total_due_execution_requests == 0
    assert next_state.emitted_request_ids == state.emitted_request_ids


def test_append_audit_creation_requests_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_execution_bridge_outputs(
        due_execution_queue=_queue_rows(),
        readiness_snapshot=_snapshot_payload(),
        readiness_alerts=_alerts_rows(),
    )

    path = tmp_path / "audit_creation_requests.jsonl"

    append_audit_creation_requests(requests=result.audit_creation_requests, path=path)
    append_audit_creation_requests(requests=result.audit_creation_requests, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[1]["tenant_id"] == "tenant-b"


def test_gate_passes_when_snapshot_not_blocked() -> None:
    snapshot = _snapshot_payload()
    snapshot["blocking_reasons"] = []
    snapshot["readiness_blocked"] = False
    snapshot["stale_evidence_alerts"] = 0
    snapshot["schedule_disabled_alerts"] = 0
    snapshot["total_alerts"] = 0

    result, _ = build_execution_bridge_outputs(
        due_execution_queue=_queue_rows(),
        readiness_snapshot=snapshot,
        readiness_alerts=[],
    )

    assert result.schedule_gate is not None
    assert result.schedule_gate.gate_status == "PASS"
    assert result.schedule_gate.schedule_runtime_ready is True
    assert result.schedule_gate.blocking_reasons == []
    assert result.schedule_gate.blocking_alert_ids == []


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "execution_bridge_state.json"
    original = ExecutionBridgeState(emitted_request_ids=["r2", "r1"])

    save_execution_bridge_state(path, original)
    loaded = load_execution_bridge_state(path)

    assert loaded.emitted_request_ids == ["r1", "r2"]


def test_write_schedule_gate_persists_json(tmp_path: Path) -> None:
    result, _ = build_execution_bridge_outputs(
        due_execution_queue=_queue_rows(),
        readiness_snapshot=_snapshot_payload(),
        readiness_alerts=_alerts_rows(),
    )

    assert result.schedule_gate is not None
    gate_path = tmp_path / "final_execution_schedule_gate.json"
    write_schedule_gate(gate_path, result.schedule_gate)

    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert payload["gate_status"] == "BLOCKED"
    assert payload["schedule_runtime_ready"] is False
    assert payload["total_due_execution_requests"] == 2


def test_loaders_sort_deterministically(tmp_path: Path) -> None:
    queue_path = tmp_path / "due_execution_queue.jsonl"
    alerts_path = tmp_path / "readiness_alerts.jsonl"
    snapshot_path = tmp_path / "readiness_snapshot.json"

    queue_path.write_text(
        json.dumps(_queue_rows()[1]) + "\n" + json.dumps(_queue_rows()[0]) + "\n",
        encoding="utf-8",
    )
    alerts_path.write_text(
        json.dumps(_alerts_rows()[1]) + "\n" + json.dumps(_alerts_rows()[0]) + "\n",
        encoding="utf-8",
    )
    snapshot_path.write_text(json.dumps(_snapshot_payload()) + "\n", encoding="utf-8")

    queue_rows = load_due_execution_queue(queue_path)
    alert_rows = load_readiness_alerts(alerts_path)
    snapshot = load_readiness_snapshot(snapshot_path)

    assert queue_rows[0]["tenant_id"] == "tenant-a"
    assert alert_rows[0]["tenant_id"] == "tenant-b"
    assert snapshot["cycle_date"] == "2026-02-15"
