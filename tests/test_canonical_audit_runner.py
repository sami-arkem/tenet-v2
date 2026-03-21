from __future__ import annotations

import json
from pathlib import Path

from core.canonical_audit_runner import (
    AuditRunnerState,
    append_jobs,
    build_audit_runner_outputs,
    load_audit_runner_state,
    load_existing_jobs,
    load_work_items,
    save_audit_runner_state,
    write_runner_index,
)


def _work_items() -> list[dict]:
    return [
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
            "payload_hash": "w1"
        },
        {
            "work_item_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "schedule_id": "sched-010",
            "due_date": "2026-02-20",
            "creation_date": "2026-02-20",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "source_request_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "source_queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "intake_status": "READY_FOR_AUDIT_EXECUTION",
            "execution_status": "NOT_STARTED",
            "release_ready": False,
            "payload_hash": "w2"
        },
    ]


def test_build_runner_outputs_creates_jobs_and_index() -> None:
    result, next_state = build_audit_runner_outputs(work_items=_work_items(), existing_jobs=[])

    assert len(result.created_jobs) == 2
    assert result.created_jobs[0].job_id == "tenant-a:aml_periodic:sched-001:2026-02-15"
    assert result.created_jobs[0].run_status == "QUEUED"

    assert result.runner_index is not None
    assert result.runner_index.total_work_items_seen == 2
    assert result.runner_index.total_new_jobs == 2
    assert result.runner_index.total_existing_jobs == 2
    assert result.runner_index.total_open_jobs == 2
    assert result.runner_index.total_completed_jobs == 0

    assert next_state.emitted_job_ids == sorted([
        "tenant-a:aml_periodic:sched-001:2026-02-15",
        "tenant-b:vendor_risk_review:sched-010:2026-02-20",
    ])


def test_runner_deduplicates_existing_jobs() -> None:
    existing = [
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
            "payload_hash": "j1"
        }
    ]

    result, _ = build_audit_runner_outputs(
        work_items=_work_items(),
        existing_jobs=existing,
        state=AuditRunnerState(emitted_job_ids=["tenant-a:aml_periodic:sched-001:2026-02-15"]),
    )

    assert len(result.created_jobs) == 1
    assert result.created_jobs[0].tenant_id == "tenant-b"
    assert result.runner_index is not None
    assert result.runner_index.total_existing_jobs == 2


def test_append_jobs_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_audit_runner_outputs(work_items=_work_items(), existing_jobs=[])

    path = tmp_path / "jobs.jsonl"
    append_jobs(jobs=result.created_jobs, path=path)
    append_jobs(jobs=result.created_jobs, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "runner_state.json"
    original = AuditRunnerState(emitted_job_ids=["j2", "j1"])

    save_audit_runner_state(path, original)
    loaded = load_audit_runner_state(path)

    assert loaded.emitted_job_ids == ["j1", "j2"]


def test_loaders_and_writer(tmp_path: Path) -> None:
    work_items_path = tmp_path / "work_items.jsonl"
    jobs_path = tmp_path / "jobs.jsonl"
    index_path = tmp_path / "runner_index.json"

    work_items_path.write_text(
        json.dumps(_work_items()[1]) + "\n" + json.dumps(_work_items()[0]) + "\n",
        encoding="utf-8",
    )

    work_items = load_work_items(work_items_path)
    result, _ = build_audit_runner_outputs(work_items=work_items, existing_jobs=[])
    append_jobs(jobs=result.created_jobs, path=jobs_path)
    assert result.runner_index is not None
    write_runner_index(index_path, result.runner_index)

    jobs = load_existing_jobs(jobs_path)
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))

    assert work_items[0]["tenant_id"] == "tenant-a"
    assert jobs[0]["tenant_id"] == "tenant-a"
    assert index_payload["total_existing_jobs"] == 2
