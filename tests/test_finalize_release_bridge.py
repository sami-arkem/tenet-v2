from __future__ import annotations

import json
from pathlib import Path

from core.finalize_release_bridge import (
    build_finalize_release_artifact,
    load_artifact,
    load_execution_records,
    write_finalize_release_artifact,
)


def _release_surface_pass() -> dict:
    return {
        "schema_version": "1.0",
        "release_status": "PASS",
        "release_ready": True,
        "final_execution_status": "PASS",
        "final_execution_ready": True,
        "report_ready": True,
        "export_ready": True,
        "total_jobs": 2,
        "total_completed_jobs": 2,
        "total_open_jobs": 0,
        "blocking_reasons": [],
        "included_artifacts": ["final_execution_discipline", "audit_runner_index", "report_gate", "export_gate"],
        "payload_hash": "release-pass",
    }


def _release_surface_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "release_status": "BLOCKED",
        "release_ready": False,
        "final_execution_status": "BLOCKED",
        "final_execution_ready": False,
        "report_ready": True,
        "export_ready": True,
        "total_jobs": 2,
        "total_completed_jobs": 0,
        "total_open_jobs": 2,
        "blocking_reasons": [
            "final_execution:final_execution_schedule_dependency_gate:stale_evidence:1",
            "audit_runner:open_jobs:2",
        ],
        "included_artifacts": ["final_execution_discipline", "audit_runner_index", "report_gate", "export_gate"],
        "payload_hash": "release-blocked",
    }


def _execution_index_complete() -> dict:
    return {
        "schema_version": "1.0",
        "total_jobs_seen": 2,
        "total_new_execution_records": 2,
        "total_existing_execution_records": 2,
        "total_completed_executions": 2,
        "total_open_executions": 0,
        "total_blocked_executions": 0,
        "tenant_counts": {"tenant-a": 1, "tenant-b": 1},
        "audit_kind_counts": {"aml_periodic": 1, "vendor_risk_review": 1},
        "payload_hash": "exec-complete",
    }


def _execution_index_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "total_jobs_seen": 2,
        "total_new_execution_records": 2,
        "total_existing_execution_records": 2,
        "total_completed_executions": 1,
        "total_open_executions": 1,
        "total_blocked_executions": 1,
        "tenant_counts": {"tenant-a": 1, "tenant-b": 1},
        "audit_kind_counts": {"aml_periodic": 1, "vendor_risk_review": 1},
        "payload_hash": "exec-blocked",
    }


def _execution_records_complete() -> list[dict]:
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
            "payload_hash": "r1",
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
            "payload_hash": "r2",
        },
    ]


def _execution_records_incomplete() -> list[dict]:
    rows = _execution_records_complete()
    rows[1] = {
        **rows[1],
        "run_status": "FAILED",
        "execution_status": "BLOCKED",
        "report_ready": False,
        "export_ready": False,
        "release_ready": False,
        "blocking_reasons": ["evidence:missing_required_pack"],
    }
    return rows


def test_finalize_blocks_on_release_surface_failure() -> None:
    artifact = build_finalize_release_artifact(
        release_surface=_release_surface_blocked(),
        execution_index=_execution_index_blocked(),
        execution_records=_execution_records_incomplete(),
    )

    assert artifact.finalize_status == "BLOCKED"
    assert artifact.finalize_ready is False
    assert artifact.release_surface_ready is False
    assert "release_surface:final_execution:final_execution_schedule_dependency_gate:stale_evidence:1" in artifact.blocking_reasons


def test_finalize_blocks_on_incomplete_execution() -> None:
    artifact = build_finalize_release_artifact(
        release_surface=_release_surface_pass(),
        execution_index=_execution_index_blocked(),
        execution_records=_execution_records_incomplete(),
    )

    assert artifact.finalize_status == "BLOCKED"
    assert artifact.finalize_ready is False
    assert artifact.execution_complete is False
    assert "audit_execution:execution_not_complete:1" in artifact.blocking_reasons
    assert "audit_execution:report_not_ready_for_all_records" in artifact.blocking_reasons
    assert "audit_execution:export_not_ready_for_all_records" in artifact.blocking_reasons


def test_finalize_passes_only_when_everything_is_complete() -> None:
    artifact = build_finalize_release_artifact(
        release_surface=_release_surface_pass(),
        execution_index=_execution_index_complete(),
        execution_records=_execution_records_complete(),
    )

    assert artifact.finalize_status == "PASS"
    assert artifact.finalize_ready is True
    assert artifact.execution_complete is True
    assert artifact.report_ready is True
    assert artifact.export_ready is True
    assert artifact.blocking_reasons == []


def test_writer_and_loaders(tmp_path: Path) -> None:
    records_path = tmp_path / "execution_records.jsonl"
    output_path = tmp_path / "finalize_release_artifact.json"

    records_path.write_text(
        json.dumps(_execution_records_complete()[1]) + "\n" + json.dumps(_execution_records_complete()[0]) + "\n",
        encoding="utf-8",
    )

    records = load_execution_records(records_path)
    assert records[0]["tenant_id"] == "tenant-a"

    artifact = build_finalize_release_artifact(
        release_surface=_release_surface_pass(),
        execution_index=_execution_index_complete(),
        execution_records=records,
    )
    write_finalize_release_artifact(output_path, artifact)
    payload = load_artifact(output_path)

    assert payload["finalize_status"] == "PASS"
    assert payload["finalize_ready"] is True
