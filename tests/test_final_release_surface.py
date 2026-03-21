from __future__ import annotations

import json
from pathlib import Path

from core.final_release_surface import (
    build_release_surface,
    load_artifact,
    load_jobs,
    write_release_surface,
)


def _final_execution_pass() -> dict:
    return {
        "schema_version": "1.0",
        "overall_status": "PASS",
        "discipline_ready": True,
        "failing_gate_names": [],
        "blocking_reasons": [],
        "evaluated_gates": [],
        "total_gates_evaluated": 5,
        "total_blocked_gates": 0,
        "total_passed_gates": 5,
        "payload_hash": "fed-pass"
    }


def _final_execution_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "overall_status": "BLOCKED",
        "discipline_ready": False,
        "failing_gate_names": ["final_execution_schedule_dependency_gate"],
        "blocking_reasons": ["final_execution_schedule_dependency_gate:stale_evidence:1"],
        "evaluated_gates": [],
        "total_gates_evaluated": 5,
        "total_blocked_gates": 1,
        "total_passed_gates": 4,
        "payload_hash": "fed-blocked"
    }


def _runner_index_open() -> dict:
    return {
        "schema_version": "1.0",
        "total_work_items_seen": 2,
        "total_new_jobs": 2,
        "total_existing_jobs": 2,
        "total_open_jobs": 2,
        "total_completed_jobs": 0,
        "tenant_counts": {"tenant-a": 1, "tenant-b": 1},
        "audit_kind_counts": {"aml_periodic": 1, "vendor_risk_review": 1},
        "payload_hash": "runner-open"
    }


def _runner_index_complete() -> dict:
    return {
        "schema_version": "1.0",
        "total_work_items_seen": 2,
        "total_new_jobs": 0,
        "total_existing_jobs": 2,
        "total_open_jobs": 0,
        "total_completed_jobs": 2,
        "tenant_counts": {"tenant-a": 1, "tenant-b": 1},
        "audit_kind_counts": {"aml_periodic": 1, "vendor_risk_review": 1},
        "payload_hash": "runner-complete"
    }


def _report_gate_pass() -> dict:
    return {
        "gate_name": "report_validation_gate",
        "gate_status": "PASS",
        "validation_ready": True,
        "blocking_reasons": [],
        "payload_hash": "report-pass"
    }


def _export_gate_pass() -> dict:
    return {
        "gate_name": "export_gate",
        "gate_status": "PASS",
        "export_ready": True,
        "blocking_reasons": [],
        "payload_hash": "export-pass"
    }


def _remediation_gate_pass() -> dict:
    return {
        "gate_name": "remediation_tracking_gate",
        "gate_status": "PASS",
        "remediation_ready": True,
        "blocking_reasons": [],
        "payload_hash": "rem-pass"
    }


def _remediation_gate_blocked() -> dict:
    return {
        "gate_name": "remediation_tracking_gate",
        "gate_status": "BLOCKED",
        "remediation_ready": False,
        "blocking_reasons": ["remediation:unresolved_release_blockers:5"],
        "payload_hash": "rem-blocked"
    }


def test_release_surface_blocks_on_remediation_failure() -> None:
    artifact = build_release_surface(
        final_execution_discipline=_final_execution_pass(),
        runner_index=_runner_index_complete(),
        remediation_gate=_remediation_gate_blocked(),
        report_gate=_report_gate_pass(),
        export_gate=_export_gate_pass(),
    )

    assert artifact.release_status == "BLOCKED"
    assert artifact.release_ready is False
    assert artifact.remediation_ready is False
    assert "remediation:remediation:unresolved_release_blockers:5" in artifact.blocking_reasons


def test_release_surface_passes_only_when_all_surfaces_pass() -> None:
    artifact = build_release_surface(
        final_execution_discipline=_final_execution_pass(),
        runner_index=_runner_index_complete(),
        remediation_gate=_remediation_gate_pass(),
        report_gate=_report_gate_pass(),
        export_gate=_export_gate_pass(),
    )

    assert artifact.release_status == "PASS"
    assert artifact.release_ready is True
    assert artifact.remediation_ready is True
    assert artifact.blocking_reasons == []


def test_writer_and_loaders(tmp_path: Path) -> None:
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        json.dumps({
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
            "payload_hash": "j2"
        }) + "\n" + json.dumps({
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
        }) + "\n",
        encoding="utf-8",
    )

    jobs = load_jobs(jobs_path)
    assert jobs[0]["tenant_id"] == "tenant-a"

    artifact = build_release_surface(
        final_execution_discipline=_final_execution_pass(),
        runner_index=_runner_index_complete(),
        remediation_gate=_remediation_gate_pass(),
        report_gate=_report_gate_pass(),
        export_gate=_export_gate_pass(),
    )

    output_path = tmp_path / "release_surface.json"
    write_release_surface(output_path, artifact)
    payload = load_artifact(output_path)

    assert payload["release_status"] == "PASS"
    assert payload["release_ready"] is True
