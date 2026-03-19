from __future__ import annotations

import json
from pathlib import Path

from core.remediation_tracking_engine import (
    RemediationTrackingState,
    append_remediation_items,
    build_remediation_tracking_outputs,
    load_canonical_reason_artifacts,
    load_execution_records,
    load_existing_remediation_items,
    load_remediation_state,
    save_remediation_state,
    write_remediation_gate,
    write_remediation_index,
)


def _canonical_reason_artifacts() -> list[dict]:
    return [
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
            "payload_hash": "r1",
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
            "blocking_reasons": [
                "evidence:missing_required_pack",
                "deterministic_decision:blocked",
            ],
            "payload_hash": "r2",
        },
    ]


def _execution_records() -> list[dict]:
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


def test_build_remediation_outputs_creates_items_and_blocks_gate() -> None:
    result, next_state = build_remediation_tracking_outputs(
        canonical_reason_artifacts=_canonical_reason_artifacts(),
        execution_records=_execution_records(),
        existing_remediation_items=[],
    )

    assert len(result.created_items) >= 5
    assert result.remediation_index is not None
    assert result.remediation_index.total_items == len(result.created_items)
    assert result.remediation_index.total_release_blocking >= 1

    assert result.remediation_gate is not None
    assert result.remediation_gate.gate_status == "BLOCKED"
    assert result.remediation_gate.remediation_ready is False
    assert result.remediation_gate.total_release_blocking_items >= 1
    assert next_state.emitted_remediation_ids


def test_deduplicates_existing_items() -> None:
    existing = [
        {
            "remediation_id": "tenant-b:vendor_risk_review:tenant-b:vendor_risk_review:sched-010:2026-02-20:reason:deterministic_decision:blocked",
            "audit_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "job_id": "tenant-b:vendor_risk_review:sched-010:2026-02-20",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "source_type": "reason",
            "source_key": "deterministic_decision:blocked",
            "severity": "CRITICAL",
            "title": "Deterministic deployment decision is blocked",
            "detail": "x",
            "status": "OPEN",
            "release_blocking": True,
            "payload_hash": "p1",
        }
    ]

    result, _ = build_remediation_tracking_outputs(
        canonical_reason_artifacts=_canonical_reason_artifacts(),
        execution_records=_execution_records(),
        existing_remediation_items=existing,
        state=RemediationTrackingState(emitted_remediation_ids=[existing[0]["remediation_id"]]),
    )

    assert result.remediation_index is not None
    assert result.remediation_index.total_items >= 1
    assert len(result.created_items) < result.remediation_index.total_items


def test_append_items_is_idempotent(tmp_path: Path) -> None:
    result, _ = build_remediation_tracking_outputs(
        canonical_reason_artifacts=_canonical_reason_artifacts(),
        execution_records=_execution_records(),
        existing_remediation_items=[],
    )

    path = tmp_path / "remediation_items.jsonl"
    append_remediation_items(items=result.created_items, path=path)
    append_remediation_items(items=result.created_items, path=path)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    ids = [row["remediation_id"] for row in rows]

    assert len(ids) == len(set(ids))


def test_state_round_trip_and_writers(tmp_path: Path) -> None:
    state_path = tmp_path / "remediation_state.json"
    items_path = tmp_path / "remediation_items.jsonl"
    artifacts_path = tmp_path / "canonical_reason_artifacts.json"
    execution_path = tmp_path / "execution_records.jsonl"
    index_path = tmp_path / "remediation_index.json"
    gate_path = tmp_path / "remediation_gate.json"

    original = RemediationTrackingState(emitted_remediation_ids=["r2", "r1"])
    save_remediation_state(state_path, original)
    loaded_state = load_remediation_state(state_path)
    assert loaded_state.emitted_remediation_ids == ["r1", "r2"]

    _payload = {
        "canonical_reason_artifacts": _canonical_reason_artifacts()
    }
    artifacts_path.write_text(json.dumps(_payload) + "\n", encoding="utf-8")
    execution_path.write_text("\n".join(json.dumps(row) for row in _execution_records()) + "\n", encoding="utf-8")

    loaded_artifacts = load_canonical_reason_artifacts(artifacts_path)
    loaded_execution = load_execution_records(execution_path)
    existing = load_existing_remediation_items(items_path)

    result, _ = build_remediation_tracking_outputs(
        canonical_reason_artifacts=loaded_artifacts,
        execution_records=loaded_execution,
        existing_remediation_items=existing,
    )

    append_remediation_items(items=result.created_items, path=items_path)
    assert result.remediation_index is not None
    assert result.remediation_gate is not None
    write_remediation_index(index_path, result.remediation_index)
    write_remediation_gate(gate_path, result.remediation_gate)

    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))

    assert index_payload["total_items"] >= 1
    assert gate_payload["gate_name"] == "remediation_tracking_gate"
