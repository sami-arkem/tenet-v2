from __future__ import annotations

import json
from pathlib import Path

from core.deterministic_audit_execution_bridge import (
    DeterministicAuditExecutionState,
    append_execution_records,
    build_execution_outputs,
    load_execution_outcomes,
    load_execution_state,
    load_existing_execution_records,
    load_jobs,
    save_execution_state,
    write_execution_index,
)


def _jobs() -> list[dict]:
    return [
        {
            "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "work_item_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "audit_kind": "aml_periodic",
            "schedule_id": "sched-001",
            "due_date": "2026-02-15",
            "creation_date": "2026-02-15",
            "intake_status": "READY_FOR_AUDIT_EXECUTION",
            "execution_status": "NOT_STARTED",
            "run_status": "QUEUED",
            "source_work_item_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "payload_hash": "j1",
        },
        {
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "work_item_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "schedule_id": "sched-010",
            "due_date": "2026-02-20",
            "creation_date": "2026-02-20",
            "intake_status": "READY_FOR_AUDIT_EXECUTION",
            "execution_status": "NOT_STARTED",
            "run_status": "QUEUED",
            "source_work_item_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "payload_hash": "j2",
        },
    ]


def _outcomes() -> dict:
    return {
        "tenant-a:aml_periodic:sched-001:2026-02-15": {
            "run_status": "COMPLETED",
            "execution_status": "COMPLETED",
            "verdict_status": "CONDITIONALLY_APPROVED",
            "report_ready": True,
            "export_ready": True,
            "release_ready": True,
            "blocking_reasons": [],
        },
        "tenant-b:vendor_risk_review:sched-010:2026-02-20": {
            "run_status": "FAILED",
            "execution_status": "BLOCKED",
            "verdict_status": "BLOCKED",
            "report_ready": False,
            "export_ready": False,
            "release_ready": False,
            "blocking_reasons": ["evidence:missing_required_pack"],
        },
    }


def test_build_execution_outputs_without_outcomes_blocks_records() -> None:
    result, next_state = build_execution_outputs(
        jobs=_jobs(),
        execution_outcomes={},
        existing_execution_records=[],
    )

    assert len(result.created_execution_records) == 2
    assert result.created_execution_records[0].execution_status == "PENDING_EXECUTION"
    assert result.created_execution_records[0].release_ready is False
    assert "deterministic_execution:not_run" in result.created_execution_records[0].blocking_reasons

    assert result.execution_index is not None
    assert result.execution_index.total_completed_executions == 0
    assert result.execution_index.total_open_executions == 2
    assert result.execution_index.total_blocked_executions == 2

    assert next_state.emitted_execution_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_build_execution_outputs_with_outcomes_reflects_real_statuses() -> None:
    result, _ = build_execution_outputs(
        jobs=_jobs(),
        execution_outcomes=_outcomes(),
        existing_execution_records=[],
    )

    assert len(result.created_execution_records) == 2

    completed = result.created_execution_records[0]
    blocked = result.created_execution_records[1]

    assert completed.tenant_id == "tenant-a"
    assert completed.execution_status == "COMPLETED"
    assert completed.report_ready is True
    assert completed.export_ready is True

    assert blocked.tenant_id == "tenant-b"
    assert blocked.execution_status == "BLOCKED"
    assert blocked.release_ready is False
    assert "evidence:missing_required_pack" in blocked.blocking_reasons

    assert result.execution_index is not None
    assert result.execution_index.total_completed_executions == 1
    assert result.execution_index.total_open_executions == 1
    assert result.execution_index.total_blocked_executions == 1


def test_execution_deduplicates_existing_records() -> None:
    existing = [
        {
            "execution_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "audit_kind": "aml_periodic",
            "schedule_id": "sched-001",
            "due_date": "2026-02-15",
            "creation_date": "2026-02-15",
            "run_status": "COMPLETED",
            "execution_status": "COMPLETED",
            "verdict_status": "CONDITIONALLY_APPROVED",
            "deterministic_engine": "reason.py",
            "source_job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "report_ready": True,
            "export_ready": True,
            "release_ready": True,
            "blocking_reasons": [],
            "payload_hash": "e1",
        }
    ]

    result, _ = build_execution_outputs(
        jobs=_jobs(),
        execution_outcomes=_outcomes(),
        existing_execution_records=existing,
        state=DeterministicAuditExecutionState(
            emitted_execution_ids=["tenant-a:aml_periodic:sched-001:2026-02-15"]
        ),
    )

    assert len(result.created_execution_records) == 1
    assert result.created_execution_records[0].tenant_id == "tenant-b"
    assert result.execution_index is not None
    assert result.execution_index.total_existing_execution_records == 2


def test_append_records_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_execution_outputs(
        jobs=_jobs(),
        execution_outcomes=_outcomes(),
        existing_execution_records=[],
    )

    path = tmp_path / "execution_records.jsonl"
    append_execution_records(records=result.created_execution_records, path=path)
    append_execution_records(records=result.created_execution_records, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2


def test_state_round_trip_and_loaders(tmp_path: Path) -> None:
    state_path = tmp_path / "execution_state.json"
    jobs_path = tmp_path / "jobs.jsonl"
    records_path = tmp_path / "execution_records.jsonl"
    outcomes_path = tmp_path / "outcomes.json"

    original = DeterministicAuditExecutionState(emitted_execution_ids=["e2", "e1"])
    save_execution_state(state_path, original)
    loaded_state = load_execution_state(state_path)
    assert loaded_state.emitted_execution_ids == ["e1", "e2"]

    jobs_path.write_text(
        json.dumps(_jobs()[1]) + "\n" + json.dumps(_jobs()[0]) + "\n",
        encoding="utf-8",
    )
    records_path.write_text(
        json.dumps({
            "execution_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "schedule_id": "sched-010",
            "due_date": "2026-02-20",
            "creation_date": "2026-02-20",
            "run_status": "FAILED",
            "execution_status": "BLOCKED",
            "verdict_status": "BLOCKED",
            "deterministic_engine": "reason.py",
            "source_job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "report_ready": False,
            "export_ready": False,
            "release_ready": False,
            "blocking_reasons": ["evidence:missing_required_pack"],
            "payload_hash": "r2"
        }) + "\n" + json.dumps({
            "execution_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "audit_kind": "aml_periodic",
            "schedule_id": "sched-001",
            "due_date": "2026-02-15",
            "creation_date": "2026-02-15",
            "run_status": "COMPLETED",
            "execution_status": "COMPLETED",
            "verdict_status": "CONDITIONALLY_APPROVED",
            "deterministic_engine": "reason.py",
            "source_job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "report_ready": True,
            "export_ready": True,
            "release_ready": True,
            "blocking_reasons": [],
            "payload_hash": "r1"
        }) + "\n",
        encoding="utf-8",
    )
    outcomes_path.write_text(json.dumps({"job_outcomes": _outcomes()}) + "\n", encoding="utf-8")

    jobs = load_jobs(jobs_path)
    records = load_existing_execution_records(records_path)
    outcomes = load_execution_outcomes(outcomes_path)

    assert jobs[0]["tenant_id"] == "tenant-a"
    assert records[0]["tenant_id"] == "tenant-a"
    assert sorted(outcomes.keys()) == sorted(_outcomes().keys())


def test_write_execution_index(tmp_path: Path) -> None:
    result, _ = build_execution_outputs(
        jobs=_jobs(),
        execution_outcomes=_outcomes(),
        existing_execution_records=[],
    )
    assert result.execution_index is not None
    index_path = tmp_path / "execution_index.json"
    write_execution_index(index_path, result.execution_index)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["total_completed_executions"] == 1
