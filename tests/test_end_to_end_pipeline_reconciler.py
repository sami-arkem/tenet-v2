from __future__ import annotations

import json
from pathlib import Path

from core.end_to_end_pipeline_reconciler import (
    build_pipeline_reconciliation_result,
    load_artifact,
    load_execution_records,
    load_jobs,
    load_materialized_audit_records,
    load_work_items,
    write_jobs,
    write_materialized_audits,
    write_production_readiness,
    write_work_items,
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
            "payload_hash": "w1",
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
            "payload_hash": "w2",
        },
    ]


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


def _materialized_audits() -> list[dict]:
    return [
        {
            "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "audit_kind": "aml_periodic",
            "creation_date": "2026-02-15",
            "due_date": "2026-02-15",
            "release_ready": False,
            "schedule_id": "sched-001",
            "source_policy_hash": "abc123",
            "source_queue_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "source_request_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
            "tenant_id": "tenant-a",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED",
            "payload_hash": "a1",
        },
        {
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_kind": "vendor_risk_review",
            "creation_date": "2026-02-20",
            "due_date": "2026-02-20",
            "release_ready": False,
            "schedule_id": "sched-010",
            "source_policy_hash": "def456",
            "source_queue_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "source_request_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "workflow_origin": "SCHEDULE_RUNTIME",
            "workflow_status": "CREATED",
            "payload_hash": "a2",
        },
    ]


def _execution_records_blocked() -> list[dict]:
    return [
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
        },
        {
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
            "payload_hash": "e2",
        },
    ]


def _execution_records_pass() -> list[dict]:
    return [
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
        },
        {
            "execution_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "schedule_id": "sched-010",
            "due_date": "2026-02-20",
            "creation_date": "2026-02-20",
            "run_status": "COMPLETED",
            "execution_status": "COMPLETED",
            "verdict_status": "APPROVED",
            "deterministic_engine": "reason.py",
            "source_job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "report_ready": True,
            "export_ready": True,
            "release_ready": True,
            "blocking_reasons": [],
            "payload_hash": "e2",
        },
    ]


def _finalization_blocked() -> dict:
    return {
        "finalization_status": "BLOCKED",
        "finalization_ready": False,
        "blocking_reasons": ["audit_execution:execution_not_complete:1"],
    }


def _finalization_pass() -> dict:
    return {
        "finalization_status": "PASS",
        "finalization_ready": True,
        "blocking_reasons": [],
    }


def test_pipeline_reconciliation_blocks_when_execution_or_finalization_blocked() -> None:
    result = build_pipeline_reconciliation_result(
        work_items=_work_items(),
        jobs=_jobs(),
        materialized_audit_records=_materialized_audits(),
        execution_records=_execution_records_blocked(),
        finalization_receipt=_finalization_blocked(),
    )

    assert result.production_readiness.readiness_status == "BLOCKED"
    assert result.production_readiness.readiness_ready is False
    assert result.reconciled_work_items[0]["intake_status"] == "AUDIT_EXECUTED"
    assert result.reconciled_work_items[1]["intake_status"] == "AUDIT_BLOCKED"
    assert result.reconciled_jobs[0]["run_status"] == "COMPLETED"
    assert result.reconciled_jobs[1]["run_status"] == "FAILED"
    assert result.reconciled_materialized_audits[0]["workflow_status"] == "EXECUTION_COMPLETED"
    assert result.reconciled_materialized_audits[1]["workflow_status"] == "EXECUTION_BLOCKED"
    assert "finalization:audit_execution:execution_not_complete:1" in result.production_readiness.blocking_reasons


def test_pipeline_reconciliation_passes_when_everything_passes() -> None:
    result = build_pipeline_reconciliation_result(
        work_items=_work_items(),
        jobs=_jobs(),
        materialized_audit_records=_materialized_audits(),
        execution_records=_execution_records_pass(),
        finalization_receipt=_finalization_pass(),
    )

    assert result.production_readiness.readiness_status == "PASS"
    assert result.production_readiness.readiness_ready is True
    assert result.production_readiness.total_completed_executions == 2
    assert result.production_readiness.total_blocked_executions == 0
    assert all(item["release_ready"] is True for item in result.reconciled_work_items)
    assert all(item["release_ready"] is True for item in result.reconciled_materialized_audits)


def test_writers_and_loaders(tmp_path: Path) -> None:
    work_items_path = tmp_path / "work_items.jsonl"
    jobs_path = tmp_path / "jobs.jsonl"
    audits_path = tmp_path / "materialized_audits.jsonl"
    execution_path = tmp_path / "execution_records.jsonl"
    receipt_path = tmp_path / "finalization_receipt.json"
    readiness_path = tmp_path / "production_readiness.json"

    work_items_path.write_text("\n".join(json.dumps(row) for row in reversed(_work_items())) + "\n", encoding="utf-8")
    jobs_path.write_text("\n".join(json.dumps(row) for row in reversed(_jobs())) + "\n", encoding="utf-8")
    audits_path.write_text("\n".join(json.dumps(row) for row in reversed(_materialized_audits())) + "\n", encoding="utf-8")
    execution_path.write_text("\n".join(json.dumps(row) for row in reversed(_execution_records_pass())) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(_finalization_pass()) + "\n", encoding="utf-8")

    work_items = load_work_items(work_items_path)
    jobs = load_jobs(jobs_path)
    audits = load_materialized_audit_records(audits_path)
    execution = load_execution_records(execution_path)
    receipt = load_artifact(receipt_path)

    result = build_pipeline_reconciliation_result(
        work_items=work_items,
        jobs=jobs,
        materialized_audit_records=audits,
        execution_records=execution,
        finalization_receipt=receipt,
    )

    write_work_items(work_items_path, result.reconciled_work_items)
    write_jobs(jobs_path, result.reconciled_jobs)
    write_materialized_audits(audits_path, result.reconciled_materialized_audits)
    write_production_readiness(readiness_path, result.production_readiness)

    written_readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    assert work_items[0]["tenant_id"] == "tenant-a"
    assert jobs[0]["tenant_id"] == "tenant-a"
    assert audits[0]["tenant_id"] == "tenant-a"
    assert execution[0]["tenant_id"] == "tenant-a"
    assert written_readiness["readiness_status"] == "PASS"
