from __future__ import annotations

import json
from pathlib import Path

from core.tenet_e2e_orchestrator import (
    TenetE2EPaths,
    run_tenet_e2e,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _raw_reason_output() -> dict:
    return {
        "results": [
            {
                "job_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
                "audit_id": "tenant-a:aml_periodic:sched-001:2026-02-15",
                "tenant_id": "tenant-a",
                "audit_kind": "aml_periodic",
                "schedule_id": "sched-001",
                "deployment_decision": "CONDITIONALLY_APPROVED",
                "findings_count": 1,
                "missing_controls_count": 0,
                "missing_evidence_count": 0,
                "review_complete": True,
                "report_ready": True,
                "export_ready": True,
                "export_verified": True,
                "blocking_reasons": [],
            },
            {
                "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
                "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
                "tenant_id": "tenant-b",
                "audit_kind": "vendor_risk_review",
                "schedule_id": "sched-010",
                "deployment_decision": "BLOCKED",
                "findings_count": 1,
                "missing_controls_count": 1,
                "missing_evidence_count": 1,
                "review_complete": False,
                "report_ready": False,
                "export_ready": False,
                "export_verified": False,
                "blocking_reasons": ["evidence:missing_required_pack"],
            },
        ]
    }


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


def _schedule_dependency_gate() -> dict:
    return {
        "schema_version": "1.0",
        "gate_name": "final_execution_schedule_dependency_gate",
        "gate_status": "PASS",
        "dependency_ready": True,
        "schedule_runtime_gate_status": "PASS",
        "schedule_runtime_ready": True,
        "blocking_reasons": [],
        "payload_hash": "sched-pass",
    }


def _runner_index() -> dict:
    return {
        "schema_version": "1.0",
        "total_work_items_seen": 2,
        "total_new_jobs": 0,
        "total_existing_jobs": 2,
        "total_open_jobs": 0,
        "total_completed_jobs": 2,
        "tenant_counts": {"tenant-a": 1, "tenant-b": 1},
        "audit_kind_counts": {"aml_periodic": 1, "vendor_risk_review": 1},
        "payload_hash": "runner-index",
    }


def _report_gate() -> dict:
    return {
        "gate_name": "report_validation_gate",
        "gate_status": "PASS",
        "validation_ready": True,
        "blocking_reasons": [],
        "payload_hash": "report-pass",
    }


def _export_gate() -> dict:
    return {
        "gate_name": "export_gate",
        "gate_status": "PASS",
        "export_ready": True,
        "blocking_reasons": [],
        "payload_hash": "export-pass",
    }


def _paths(tmp_path: Path) -> TenetE2EPaths:
    return TenetE2EPaths(
        raw_reason_output=str(tmp_path / "raw_reason_output.json"),
        canonical_reason_artifacts=str(tmp_path / "canonical_reason_artifacts.json"),
        execution_outcomes=str(tmp_path / "execution_outcomes.json"),
        jobs=str(tmp_path / "jobs.jsonl"),
        execution_state=str(tmp_path / "execution_state.json"),
        execution_records=str(tmp_path / "execution_records.jsonl"),
        execution_index=str(tmp_path / "execution_index.json"),
        remediation_state=str(tmp_path / "remediation_state.json"),
        remediation_items=str(tmp_path / "remediation_items.jsonl"),
        remediation_index=str(tmp_path / "remediation_index.json"),
        remediation_gate=str(tmp_path / "remediation_gate.json"),
        schedule_dependency_gate=str(tmp_path / "schedule_dependency_gate.json"),
        final_execution_discipline=str(tmp_path / "final_execution_discipline.json"),
        runner_index=str(tmp_path / "runner_index.json"),
        report_gate=str(tmp_path / "report_gate.json"),
        export_gate=str(tmp_path / "export_gate.json"),
        release_surface=str(tmp_path / "release_surface.json"),
        finalize_release_artifact=str(tmp_path / "finalize_release_artifact.json"),
        finalize_decision=str(tmp_path / "finalize_decision.json"),
        immutable_release_package=str(tmp_path / "immutable_release_package.json"),
        finalization_receipt=str(tmp_path / "finalization_receipt.json"),
        work_items=str(tmp_path / "work_items.jsonl"),
        materialized_audits=str(tmp_path / "materialized_audits.jsonl"),
        production_readiness=str(tmp_path / "production_readiness.json"),
    )


def _seed_files(tmp_path: Path) -> TenetE2EPaths:
    paths = _paths(tmp_path)
    _write_json(Path(paths.raw_reason_output), _raw_reason_output())
    _write_jsonl(Path(paths.jobs), _jobs())
    _write_jsonl(Path(paths.work_items), _work_items())
    _write_jsonl(Path(paths.materialized_audits), _materialized_audits())
    _write_json(Path(paths.schedule_dependency_gate), _schedule_dependency_gate())
    _write_json(Path(paths.runner_index), _runner_index())
    _write_json(Path(paths.report_gate), _report_gate())
    _write_json(Path(paths.export_gate), _export_gate())
    return paths


def test_e2e_pipeline_blocks_when_remediation_blocks(tmp_path: Path) -> None:
    paths = _seed_files(tmp_path)
    result = run_tenet_e2e(paths)

    assert result.overall_status == "BLOCKED"
    assert result.overall_ready is False

    remediation_gate = json.loads(Path(paths.remediation_gate).read_text(encoding="utf-8"))
    final_execution = json.loads(Path(paths.final_execution_discipline).read_text(encoding="utf-8"))
    release_surface = json.loads(Path(paths.release_surface).read_text(encoding="utf-8"))
    readiness = json.loads(Path(paths.production_readiness).read_text(encoding="utf-8"))

    assert remediation_gate["gate_status"] == "BLOCKED"
    assert "remediation_tracking_gate" in final_execution["failing_gate_names"]
    assert release_surface["release_status"] == "BLOCKED"
    assert readiness["readiness_status"] == "BLOCKED"
