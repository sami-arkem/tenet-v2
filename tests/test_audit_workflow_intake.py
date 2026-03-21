from __future__ import annotations

import json
from pathlib import Path

from core.audit_workflow_intake import (
    AuditWorkflowIntakeState,
    append_audit_workflow_work_items,
    build_audit_workflow_intake_outputs,
    load_audit_workflow_intake_state,
    load_existing_work_items,
    load_materialized_audit_records,
    save_audit_workflow_intake_state,
    write_audit_workflow_index,
)


def _materialized_records() -> list[dict]:
    return [
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
            "workflow_status": "CREATED"
        },
        {
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_kind": "vendor_risk_review",
            "creation_date": "2026-02-20",
            "due_date": "2026-02-20",
            "payload_hash": "x2",
            "release_ready": False,
            "schedule_id": "sched-010",
            "source_policy_hash": "def456",
            "source_queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "source_request_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED"
        },
    ]


def test_build_intake_outputs_creates_work_items_and_index() -> None:
    result, next_state = build_audit_workflow_intake_outputs(
        materialized_audit_records=_materialized_records(),
        existing_work_items=[],
    )

    assert len(result.created_work_items) == 2
    assert result.created_work_items[0].work_item_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert result.created_work_items[0].intake_status == "READY_FOR_AUDIT_EXECUTION"
    assert result.created_work_items[0].execution_status == "NOT_STARTED"

    assert result.workflow_index is not None
    assert result.workflow_index.total_records_seen == 2
    assert result.workflow_index.total_new_work_items == 2
    assert result.workflow_index.total_existing_work_items == 2
    assert result.workflow_index.total_open_work_items == 2
    assert result.workflow_index.tenant_counts == {"tenant-a": 1, "tenant-b": 1}

    assert next_state.emitted_work_item_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_intake_deduplicates_existing_work_items() -> None:
    existing = [
        {
            "work_item_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "audit_kind": "aml_periodic",
            "schedule_id": "sched-001",
            "due_date": "2026-02-15",
            "creation_date": "2026-02-15",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "source_request_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "source_queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "intake_status": "READY_FOR_AUDIT_EXECUTION",
            "execution_status": "NOT_STARTED",
            "release_ready": False,
            "payload_hash": "h1"
        }
    ]

    result, _ = build_audit_workflow_intake_outputs(
        materialized_audit_records=_materialized_records(),
        existing_work_items=existing,
        state=AuditWorkflowIntakeState(
            emitted_work_item_ids=["tenant-a:aml_periodic:sched-001:2026-02-15"]
        ),
    )

    assert len(result.created_work_items) == 1
    assert result.created_work_items[0].tenant_id == "tenant-b"
    assert result.workflow_index is not None
    assert result.workflow_index.total_existing_work_items == 2


def test_append_work_items_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_audit_workflow_intake_outputs(
        materialized_audit_records=_materialized_records(),
        existing_work_items=[],
    )

    path = tmp_path / "work_items.jsonl"
    append_audit_workflow_work_items(work_items=result.created_work_items, path=path)
    append_audit_workflow_work_items(work_items=result.created_work_items, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "intake_state.json"
    original = AuditWorkflowIntakeState(emitted_work_item_ids=["w2", "w1"])

    save_audit_workflow_intake_state(path, original)
    loaded = load_audit_workflow_intake_state(path)

    assert loaded.emitted_work_item_ids == ["w1", "w2"]


def test_writers_and_loaders(tmp_path: Path) -> None:
    records_path = tmp_path / "materialized_audit_records.jsonl"
    work_items_path = tmp_path / "work_items.jsonl"
    index_path = tmp_path / "workflow_index.json"

    records_path.write_text(
        json.dumps(_materialized_records()[1]) + "\n" + json.dumps(_materialized_records()[0]) + "\n",
        encoding="utf-8",
    )

    records = load_materialized_audit_records(records_path)
    result, _ = build_audit_workflow_intake_outputs(
        materialized_audit_records=records,
        existing_work_items=[],
    )
    append_audit_workflow_work_items(work_items=result.created_work_items, path=work_items_path)
    assert result.workflow_index is not None
    write_audit_workflow_index(index_path, result.workflow_index)

    loaded_work_items = load_existing_work_items(work_items_path)
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))

    assert records[0]["tenant_id"] == "tenant-a"
    assert loaded_work_items[0]["tenant_id"] == "tenant-a"
    assert index_payload["total_existing_work_items"] == 2
