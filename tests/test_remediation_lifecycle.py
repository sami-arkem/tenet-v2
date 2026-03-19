from __future__ import annotations

import json
from pathlib import Path

from core.remediation_lifecycle import (
    apply_verification_result,
    assign_owner,
    initialize_lifecycle_items,
    initialize_timeline,
    load_gate,
    load_lifecycle_items,
    load_timeline,
    recompute_lifecycle_artifacts,
    transition_status,
    submit_for_verification,
    write_lifecycle_gate,
    write_lifecycle_index,
    write_lifecycle_items,
    write_timeline,
)


def _base_items() -> list[dict]:
    return [
        {
            "remediation_id": "tenant-b:vendor_risk_review:audit-1:reason:deterministic_decision:blocked",
            "audit_id": "audit-1",
            "job_id": "job-1",
            "tenant_id": "tenant-b",
            "audit_kind": "vendor_risk_review",
            "source_type": "reason",
            "source_key": "deterministic_decision:blocked",
            "severity": "CRITICAL",
            "title": "Deterministic deployment decision is blocked",
            "detail": "Audit audit-1 for tenant tenant-b has unresolved remediation reason: deterministic_decision:blocked.",
            "status": "OPEN",
            "release_blocking": True,
        }
    ]


def test_initialize_and_recompute() -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")
    index_artifact, gate_artifact = recompute_lifecycle_artifacts(
        lifecycle_items=items,
        today="2026-03-19",
    )

    assert len(items) == 1
    assert len(timeline) == 1
    assert index_artifact.total_open == 1
    assert gate_artifact.gate_status == "BLOCKED"


def test_assign_owner_requires_note_and_logs_timeline() -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")

    updated_items, updated_timeline = assign_owner(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        owner_user_id="user-123",
        actor_user_id="admin-1",
        note="Assigning this item to the compliance manager.",
        now="2026-03-19T11:00:00Z",
    )

    assert updated_items[0]["owner_user_id"] == "user-123"
    assert len(updated_timeline) == 2
    assert updated_timeline[-1]["action"] == "OWNER_ASSIGNED"


def test_invalid_transition_is_rejected() -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")

    try:
        transition_status(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=items[0]["remediation_id"],
            to_status="CLOSED",
            actor_user_id="admin-1",
            note="Closing immediately without the required flow.",
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Invalid status transition" in str(exc)


def test_evidence_submitted_requires_attachment_and_enters_verifying() -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")

    items, timeline = transition_status(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        to_status="IN_PROGRESS",
        actor_user_id="user-123",
        note="Starting remediation work on this blocker.",
        now="2026-03-19T11:00:00Z",
    )

    try:
        submit_for_verification(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=items[0]["remediation_id"],
            actor_user_id="user-123",
            note="Submitting for review now.",
            evidence_file_ids=[],
            now="2026-03-19T12:00:00Z",
        )
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Please attach remediation evidence" in str(exc)

    updated_items, updated_timeline = submit_for_verification(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        actor_user_id="user-123",
        note="Submitting with remediation evidence attached.",
        evidence_file_ids=["file-a", "file-b"],
        now="2026-03-19T12:00:00Z",
    )

    assert updated_items[0]["status"] == "VERIFYING"
    assert updated_items[0]["evidence_file_ids"] == ["file-a", "file-b"]
    assert updated_timeline[-1]["action"] == "VERIFICATION_QUEUED"


def test_verification_pass_closes_and_fail_reopens() -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")

    items, timeline = transition_status(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        to_status="IN_PROGRESS",
        actor_user_id="user-123",
        note="Starting remediation work on this blocker.",
        now="2026-03-19T11:00:00Z",
    )
    items, timeline = submit_for_verification(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        actor_user_id="user-123",
        note="Submitting with remediation evidence attached.",
        evidence_file_ids=["file-a"],
        now="2026-03-19T12:00:00Z",
    )

    passed_items, passed_timeline = apply_verification_result(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        verification_passed=True,
        now="2026-03-19T13:00:00Z",
    )
    assert passed_items[0]["status"] == "CLOSED"
    assert passed_timeline[-1]["to_status"] == "CLOSED"

    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")
    items, timeline = transition_status(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        to_status="IN_PROGRESS",
        actor_user_id="user-123",
        note="Starting remediation work on this blocker.",
        now="2026-03-19T11:00:00Z",
    )
    items, timeline = submit_for_verification(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        actor_user_id="user-123",
        note="Submitting with remediation evidence attached.",
        evidence_file_ids=["file-a"],
        now="2026-03-19T12:00:00Z",
    )
    failed_items, failed_timeline = apply_verification_result(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=items[0]["remediation_id"],
        verification_passed=False,
        updated_gap_note="Verification failed — updated gap remains unresolved.",
        now="2026-03-19T13:00:00Z",
    )
    assert failed_items[0]["status"] == "IN_PROGRESS"
    assert failed_items[0]["detail"] == "Verification failed — updated gap remains unresolved."
    assert failed_timeline[-1]["to_status"] == "IN_PROGRESS"


def test_writers_and_loaders(tmp_path: Path) -> None:
    items = initialize_lifecycle_items(_base_items(), now="2026-03-19T10:00:00Z")
    timeline = initialize_timeline(items, now="2026-03-19T10:00:00Z")
    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=items, today="2026-03-19")

    items_path = tmp_path / "items.jsonl"
    timeline_path = tmp_path / "timeline.jsonl"
    index_path = tmp_path / "index.json"
    gate_path = tmp_path / "gate.json"

    write_lifecycle_items(items_path, items)
    write_timeline(timeline_path, timeline)
    write_lifecycle_index(index_path, index_artifact)
    write_lifecycle_gate(gate_path, gate_artifact)

    loaded_items = load_lifecycle_items(items_path)
    loaded_timeline = load_timeline(timeline_path)
    loaded_gate = load_gate(gate_path)

    assert loaded_items[0]["remediation_id"] == items[0]["remediation_id"]
    assert loaded_timeline[0]["action"] == "CREATED"
    assert loaded_gate["gate_name"] == "remediation_tracking_gate"
