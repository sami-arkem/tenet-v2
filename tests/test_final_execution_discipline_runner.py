from __future__ import annotations

import json
from pathlib import Path

from core.final_execution_discipline_runner import (
    build_final_execution_discipline,
    load_gate_artifact,
    write_final_execution_discipline,
)


def _schedule_dependency_gate_pass() -> dict:
    return {
        "schema_version": "1.0",
        "gate_name": "final_execution_schedule_dependency_gate",
        "gate_status": "PASS",
        "dependency_ready": True,
        "schedule_runtime_gate_status": "PASS",
        "schedule_runtime_ready": True,
        "total_requests_seen": 2,
        "total_records_created_now": 2,
        "total_existing_audit_records": 2,
        "pending_request_ids": [],
        "blocking_reasons": [],
        "inherited_blocking_reasons": [],
        "payload_hash": "sched-pass"
    }


def _schedule_dependency_gate_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "gate_name": "final_execution_schedule_dependency_gate",
        "gate_status": "BLOCKED",
        "dependency_ready": False,
        "schedule_runtime_gate_status": "BLOCKED",
        "schedule_runtime_ready": False,
        "total_requests_seen": 2,
        "total_records_created_now": 2,
        "total_existing_audit_records": 2,
        "pending_request_ids": [],
        "blocking_reasons": ["stale_evidence:1"],
        "inherited_blocking_reasons": ["stale_evidence:1"],
        "payload_hash": "sched-blocked"
    }


def _remediation_gate_pass() -> dict:
    return {
        "schema_version": "1.0",
        "gate_name": "remediation_tracking_gate",
        "gate_status": "PASS",
        "remediation_ready": True,
        "total_open_items": 0,
        "total_release_blocking_items": 0,
        "unresolved_release_blockers": [],
        "blocking_reasons": [],
        "payload_hash": "rem-pass",
    }


def _remediation_gate_blocked() -> dict:
    return {
        "schema_version": "1.0",
        "gate_name": "remediation_tracking_gate",
        "gate_status": "BLOCKED",
        "remediation_ready": False,
        "total_open_items": 5,
        "total_release_blocking_items": 5,
        "unresolved_release_blockers": ["r1", "r2"],
        "blocking_reasons": ["remediation:unresolved_release_blockers:5"],
        "payload_hash": "rem-blocked",
    }


def _simple_pass_gate(name: str, ready_key: str) -> dict:
    return {
        "gate_name": name,
        "gate_status": "PASS",
        ready_key: True,
        "blocking_reasons": [],
        "payload_hash": f"{name}-pass",
    }


def test_final_execution_discipline_passes_when_all_gates_pass() -> None:
    artifact = build_final_execution_discipline(
        schedule_dependency_gate=_schedule_dependency_gate_pass(),
        remediation_gate=_remediation_gate_pass(),
        export_gate=_simple_pass_gate("export_gate", "export_ready"),
        report_validation_gate=_simple_pass_gate("report_validation_gate", "validation_ready"),
    )

    assert artifact.overall_status == "PASS"
    assert artifact.discipline_ready is True
    assert artifact.total_gates_evaluated == 4
    assert artifact.total_blocked_gates == 0


def test_final_execution_discipline_blocks_on_remediation_gate() -> None:
    artifact = build_final_execution_discipline(
        schedule_dependency_gate=_schedule_dependency_gate_pass(),
        remediation_gate=_remediation_gate_blocked(),
    )

    assert artifact.overall_status == "BLOCKED"
    assert artifact.discipline_ready is False
    assert "remediation_tracking_gate" in artifact.failing_gate_names
    assert "remediation_tracking_gate:remediation:unresolved_release_blockers:5" in artifact.blocking_reasons


def test_writer_and_loader_round_trip(tmp_path: Path) -> None:
    artifact = build_final_execution_discipline(
        schedule_dependency_gate=_schedule_dependency_gate_pass(),
        remediation_gate=_remediation_gate_pass(),
    )

    path = tmp_path / "final_execution_discipline.json"
    write_final_execution_discipline(path, artifact)
    payload = load_gate_artifact(path)

    assert payload["overall_status"] == "PASS"
    assert payload["discipline_ready"] is True
