from __future__ import annotations

import json
from pathlib import Path

from core.audit_schedule_audit_materialization import (
    AuditMaterializationState,
    append_audit_workflow_records,
    build_audit_materialization_outputs,
    load_audit_creation_requests,
    load_audit_materialization_state,
    load_existing_audit_records,
    load_schedule_gate,
    save_audit_materialization_state,
    write_final_execution_dependency_gate,
    write_materialization_summary,
)


def _audit_creation_requests() -> list[dict]:
    return [
        {
            "audit_kind": "aml_periodic",
            "due_date": "2026-02-15",
            "execution_date": "2026-02-15",
            "payload_hash": "c1",
            "request_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "schedule_id": "sched-001",
            "source_policy_hash": "abc123",
            "source_queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "workflow_status": "PENDING_AUDIT_CREATION",
        },
        {
            "audit_kind": "vendor_risk_review",
            "due_date": "2026-02-20",
            "execution_date": "2026-02-20",
            "payload_hash": "c2",
            "request_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "schedule_id": "sched-010",
            "source_policy_hash": "def456",
            "source_queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "workflow_status": "PENDING_AUDIT_CREATION",
        },
    ]


def _schedule_gate_blocked() -> dict:
    return {
        "blocking_alert_ids": [
            "tenant-b:sanctions_review:sched-002:STALE_EVIDENCE:2026-02-01",
        ],
        "blocking_reasons": [
            "stale_evidence:1",
        ],
        "gate_name": "audit_schedule_runtime_gate",
        "gate_status": "BLOCKED",
        "invalid_configuration_alerts": 0,
        "payload_hash": "gate1",
        "schedule_disabled_alerts": 0,
        "schedule_runtime_ready": False,
        "schema_version": "1.0",
        "stale_evidence_alerts": 1,
        "total_alerts": 1,
        "total_due_execution_requests": 2,
        "total_notifications": 2,
    }


def _schedule_gate_pass() -> dict:
    return {
        "blocking_alert_ids": [],
        "blocking_reasons": [],
        "gate_name": "audit_schedule_runtime_gate",
        "gate_status": "PASS",
        "invalid_configuration_alerts": 0,
        "payload_hash": "gate2",
        "schedule_disabled_alerts": 0,
        "schedule_runtime_ready": True,
        "schema_version": "1.0",
        "stale_evidence_alerts": 0,
        "total_alerts": 0,
        "total_due_execution_requests": 2,
        "total_notifications": 2,
    }


def test_build_materialization_outputs_creates_audit_records() -> None:
    result, next_state = build_audit_materialization_outputs(
        audit_creation_requests=_audit_creation_requests(),
        schedule_gate=_schedule_gate_pass(),
        existing_audit_records=[],
    )

    assert len(result.created_records) == 2
    assert result.created_records[0].audit_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert result.created_records[0].workflow_origin == "SCHEDULE_RUNTIME"
    assert result.created_records[0].workflow_status == "CREATED"
    assert result.created_records[0].release_ready is False

    assert result.materialization_summary is not None
    assert result.materialization_summary.total_requests_seen == 2
    assert result.materialization_summary.total_records_created_now == 2
    assert result.materialization_summary.total_records_deduplicated == 0
    assert result.materialization_summary.materialization_complete is True

    assert result.dependency_gate is not None
    assert result.dependency_gate.gate_status == "PASS"
    assert result.dependency_gate.dependency_ready is True
    assert result.dependency_gate.schedule_runtime_gate_status == "PASS"
    assert result.dependency_gate.total_existing_audit_records == 2

    assert next_state.materialized_request_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_materialization_inherits_blocked_schedule_gate() -> None:
    result, _ = build_audit_materialization_outputs(
        audit_creation_requests=_audit_creation_requests(),
        schedule_gate=_schedule_gate_blocked(),
        existing_audit_records=[],
    )

    assert result.dependency_gate is not None
    assert result.dependency_gate.gate_status == "BLOCKED"
    assert result.dependency_gate.dependency_ready is False
    assert result.dependency_gate.inherited_blocking_reasons == ["stale_evidence:1"]
    assert result.dependency_gate.blocking_reasons == ["stale_evidence:1"]


def test_materialization_deduplicates_existing_records() -> None:
    existing = [
        {
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_kind": "aml_periodic",
            "creation_date": "2026-02-15",
            "due_date": "2026-02-15",
            "payload_hash": "x1",
            "release_ready": False,
            "schedule_id": "sched-001",
            "source_policy_hash": "abc123",
            "source_queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "source_request_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED",
        }
    ]

    result, next_state = build_audit_materialization_outputs(
        audit_creation_requests=_audit_creation_requests(),
        schedule_gate=_schedule_gate_pass(),
        existing_audit_records=existing,
        state=AuditMaterializationState(
            materialized_request_ids=["tenant-a:aml_periodic:sched-001:2026-02-15"]
        ),
    )

    assert len(result.created_records) == 1
    assert result.created_records[0].tenant_id == "tenant-b"
    assert result.materialization_summary is not None
    assert result.materialization_summary.total_records_deduplicated == 1
    assert result.materialization_summary.total_records_existing_after_write == 2
    assert next_state.materialized_request_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_append_audit_workflow_records_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_audit_materialization_outputs(
        audit_creation_requests=_audit_creation_requests(),
        schedule_gate=_schedule_gate_pass(),
        existing_audit_records=[],
    )

    path = tmp_path / "materialized_audit_records.jsonl"
    append_audit_workflow_records(records=result.created_records, path=path)
    append_audit_workflow_records(records=result.created_records, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[1]["tenant_id"] == "tenant-b"


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "audit_materialization_state.json"
    original = AuditMaterializationState(
        materialized_request_ids=["r2", "r1"],
    )

    save_audit_materialization_state(path, original)
    loaded = load_audit_materialization_state(path)

    assert loaded.materialized_request_ids == ["r1", "r2"]


def test_writers_persist_summary_and_dependency_gate(tmp_path: Path) -> None:
    result, _ = build_audit_materialization_outputs(
        audit_creation_requests=_audit_creation_requests(),
        schedule_gate=_schedule_gate_pass(),
        existing_audit_records=[],
    )

    assert result.materialization_summary is not None
    assert result.dependency_gate is not None

    summary_path = tmp_path / "audit_materialization_summary.json"
    gate_path = tmp_path / "final_execution_schedule_dependency_gate.json"

    write_materialization_summary(summary_path, result.materialization_summary)
    write_final_execution_dependency_gate(gate_path, result.dependency_gate)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    assert summary["total_records_created_now"] == 2
    assert summary["materialization_complete"] is True
    assert gate["gate_status"] == "PASS"
    assert gate["dependency_ready"] is True


def test_loaders_sort_deterministically(tmp_path: Path) -> None:
    requests_path = tmp_path / "audit_creation_requests.jsonl"
    gate_path = tmp_path / "final_execution_schedule_gate.json"
    records_path = tmp_path / "materialized_audit_records.jsonl"

    requests_path.write_text(
        json.dumps(_audit_creation_requests()[1]) + "\n" + json.dumps(_audit_creation_requests()[0]) + "\n",
        encoding="utf-8",
    )
    gate_path.write_text(json.dumps(_schedule_gate_pass()) + "\n", encoding="utf-8")
    records_path.write_text(
        json.dumps({
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_kind": "vendor_risk_review",
            "creation_date": "2026-02-20",
            "due_date": "2026-02-20",
            "payload_hash": "abc",
            "release_ready": False,
            "schedule_id": "sched-010",
            "source_policy_hash": "def456",
            "source_queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "source_request_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED"
        }) + "\n" + json.dumps({
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_kind": "aml_periodic",
            "creation_date": "2026-02-15",
            "due_date": "2026-02-15",
            "payload_hash": "def",
            "release_ready": False,
            "schedule_id": "sched-001",
            "source_policy_hash": "abc123",
            "source_queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "source_request_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED"
        }) + "\n",
        encoding="utf-8",
    )

    requests = load_audit_creation_requests(requests_path)
    gate = load_schedule_gate(gate_path)
    existing = load_existing_audit_records(records_path)

    assert requests[0]["tenant_id"] == "tenant-a"
    assert gate["gate_status"] == "PASS"
    assert existing[0]["tenant_id"] == "tenant-a"
