from __future__ import annotations

import json
from pathlib import Path

from core.remediation_operator_service import (
    RemediationOperatorPaths,
    assign_owner_api,
    apply_verification_result_api,
    bootstrap_from_generated_remediation,
    get_remediation_detail,
    list_remediations,
    load_actor_directory,
    load_evidence_metadata,
    load_notification_outbox,
    load_operator_audit_log,
    set_due_date_api,
    transition_status_api,
)
from core.remediation_lifecycle import load_gate


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _generated_items() -> list[dict]:
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


def _actor_directory() -> dict:
    return {
        "users": {
            "admin-1": {"tenant_id": "tenant-b", "role": "ADMIN"},
            "owner-1": {"tenant_id": "tenant-b", "role": "OWNER"},
            "analyst-1": {"tenant_id": "tenant-b", "role": "ANALYST"},
            "viewer-1": {"tenant_id": "tenant-b", "role": "VIEWER"},
            "outsider-1": {"tenant_id": "tenant-x", "role": "ADMIN"},
        }
    }


def _paths(tmp_path: Path) -> RemediationOperatorPaths:
    return RemediationOperatorPaths(
        items=str(tmp_path / "remediation_items_operator.jsonl"),
        timeline=str(tmp_path / "remediation_timeline.jsonl"),
        lifecycle_index=str(tmp_path / "remediation_lifecycle_index.json"),
        gate=str(tmp_path / "remediation_gate.json"),
        evidence_metadata=str(tmp_path / "remediation_evidence_metadata.jsonl"),
        notification_outbox=str(tmp_path / "remediation_notification_outbox.jsonl"),
        operator_audit_log=str(tmp_path / "remediation_operator_audit_log.jsonl"),
    )


def _bootstrap(tmp_path: Path) -> tuple[dict, RemediationOperatorPaths, str]:
    generated_path = tmp_path / "generated_items.jsonl"
    actors_path = tmp_path / "actors.json"
    _write_jsonl(generated_path, _generated_items())
    _write_json(actors_path, _actor_directory())
    paths = _paths(tmp_path)
    bootstrap_from_generated_remediation(
        generated_items_path=generated_path,
        operator_paths=paths,
        now="2026-03-19T10:00:00Z",
        today="2026-03-19",
    )
    remediation_id = _generated_items()[0]["remediation_id"]
    actors = load_actor_directory(actors_path)
    return actors, paths, remediation_id


def test_list_and_detail_require_auth_and_tenant_scope(tmp_path: Path) -> None:
    actors, paths, remediation_id = _bootstrap(tmp_path)

    rows = list_remediations(
        actor_directory=actors,
        actor_user_id="viewer-1",
        items_path=Path(paths.items),
    )
    assert len(rows) == 1

    detail = get_remediation_detail(
        actor_directory=actors,
        actor_user_id="viewer-1",
        remediation_id=remediation_id,
        items_path=Path(paths.items),
        timeline_path=Path(paths.timeline),
        evidence_metadata_path=Path(paths.evidence_metadata),
    )
    assert detail["remediation"]["remediation_id"] == remediation_id

    try:
        get_remediation_detail(
            actor_directory=actors,
            actor_user_id="outsider-1",
            remediation_id=remediation_id,
            items_path=Path(paths.items),
            timeline_path=Path(paths.timeline),
            evidence_metadata_path=Path(paths.evidence_metadata),
        )
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass


def test_assign_owner_and_set_due_date_emit_audit_log_and_notifications(tmp_path: Path) -> None:
    actors, paths, remediation_id = _bootstrap(tmp_path)

    assign_result = assign_owner_api(
        actor_directory=actors,
        actor_user_id="admin-1",
        remediation_id=remediation_id,
        owner_user_id="analyst-1",
        note="Assigning this remediation to the analyst for follow-up.",
        operator_paths=paths,
        now="2026-03-19T11:00:00Z",
        today="2026-03-19",
    )
    assert assign_result["owner_user_id"] == "analyst-1"

    due_result = set_due_date_api(
        actor_directory=actors,
        actor_user_id="owner-1",
        remediation_id=remediation_id,
        due_date="2026-03-25",
        note="Setting a due date for completion before the next review.",
        operator_paths=paths,
        now="2026-03-19T12:00:00Z",
        today="2026-03-19",
    )
    assert due_result["due_date"] == "2026-03-25"

    notifications = load_notification_outbox(Path(paths.notification_outbox))
    audit_log = load_operator_audit_log(Path(paths.operator_audit_log))

    assert len(notifications) == 2
    assert len(audit_log) == 2
    assert notifications[0]["event_type"] == "REMEDIATION_OWNER_ASSIGNED"
    assert notifications[1]["event_type"] == "REMEDIATION_DUE_DATE_SET"


def test_owner_bound_transition_and_evidence_metadata_flow(tmp_path: Path) -> None:
    actors, paths, remediation_id = _bootstrap(tmp_path)

    assign_owner_api(
        actor_directory=actors,
        actor_user_id="admin-1",
        remediation_id=remediation_id,
        owner_user_id="analyst-1",
        note="Assigning this remediation to the analyst for follow-up.",
        operator_paths=paths,
        now="2026-03-19T11:00:00Z",
        today="2026-03-19",
    )

    transition_status_api(
        actor_directory=actors,
        actor_user_id="analyst-1",
        remediation_id=remediation_id,
        to_status="IN_PROGRESS",
        note="Starting work on the remediation immediately.",
        operator_paths=paths,
        now="2026-03-19T12:00:00Z",
        today="2026-03-19",
    )

    result = transition_status_api(
        actor_directory=actors,
        actor_user_id="analyst-1",
        remediation_id=remediation_id,
        to_status="EVIDENCE_SUBMITTED",
        note="Submitting remediation evidence for verification now.",
        operator_paths=paths,
        evidence_files=[
            {
                "file_id": "file-1",
                "filename": "policy-v2.pdf",
                "content_type": "application/pdf",
                "sha256": "abc123",
                "byte_size": 1200,
            },
            {
                "file_id": "file-2",
                "filename": "controls.csv",
                "content_type": "text/csv",
                "sha256": "def456",
                "byte_size": 2400,
            },
        ],
        now="2026-03-19T13:00:00Z",
        today="2026-03-19",
    )
    assert result["to_status"] == "EVIDENCE_SUBMITTED"

    evidence_rows = load_evidence_metadata(Path(paths.evidence_metadata))
    notifications = load_notification_outbox(Path(paths.notification_outbox))

    assert len(evidence_rows) == 2
    assert notifications[-1]["event_type"] == "REMEDIATION_EVIDENCE_SUBMITTED"


def test_verification_result_closes_item_and_unblocks_gate(tmp_path: Path) -> None:
    actors, paths, remediation_id = _bootstrap(tmp_path)

    assign_owner_api(
        actor_directory=actors,
        actor_user_id="admin-1",
        remediation_id=remediation_id,
        owner_user_id="analyst-1",
        note="Assigning this remediation to the analyst for follow-up.",
        operator_paths=paths,
        now="2026-03-19T11:00:00Z",
        today="2026-03-19",
    )
    transition_status_api(
        actor_directory=actors,
        actor_user_id="analyst-1",
        remediation_id=remediation_id,
        to_status="IN_PROGRESS",
        note="Starting work on the remediation immediately.",
        operator_paths=paths,
        now="2026-03-19T12:00:00Z",
        today="2026-03-19",
    )
    transition_status_api(
        actor_directory=actors,
        actor_user_id="analyst-1",
        remediation_id=remediation_id,
        to_status="EVIDENCE_SUBMITTED",
        note="Submitting remediation evidence for verification now.",
        operator_paths=paths,
        evidence_files=[
            {
                "file_id": "file-1",
                "filename": "policy-v2.pdf",
                "content_type": "application/pdf",
                "sha256": "abc123",
                "byte_size": 1200,
            }
        ],
        now="2026-03-19T13:00:00Z",
        today="2026-03-19",
    )

    result = apply_verification_result_api(
        actor_directory=actors,
        actor_user_id="owner-1",
        remediation_id=remediation_id,
        verification_passed=True,
        updated_gap_note=None,
        operator_paths=paths,
        now="2026-03-19T14:00:00Z",
        today="2026-03-19",
    )
    assert result["verification_passed"] is True

    gate = load_gate(Path(paths.gate))
    detail = get_remediation_detail(
        actor_directory=actors,
        actor_user_id="viewer-1",
        remediation_id=remediation_id,
        items_path=Path(paths.items),
        timeline_path=Path(paths.timeline),
        evidence_metadata_path=Path(paths.evidence_metadata),
    )

    assert gate["gate_status"] == "PASS"
    assert detail["remediation"]["status"] == "CLOSED"


def test_auth_before_logic_and_owner_constraints(tmp_path: Path) -> None:
    actors, paths, remediation_id = _bootstrap(tmp_path)

    try:
        assign_owner_api(
            actor_directory=actors,
            actor_user_id="viewer-1",
            remediation_id=remediation_id,
            owner_user_id="analyst-1",
            note="Viewer should not be allowed to assign ownership.",
            operator_paths=paths,
            now="2026-03-19T11:00:00Z",
            today="2026-03-19",
        )
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass

    assign_owner_api(
        actor_directory=actors,
        actor_user_id="admin-1",
        remediation_id=remediation_id,
        owner_user_id="analyst-1",
        note="Assigning this remediation to the analyst for follow-up.",
        operator_paths=paths,
        now="2026-03-19T11:00:00Z",
        today="2026-03-19",
    )

    try:
        transition_status_api(
            actor_directory=actors,
            actor_user_id="viewer-1",
            remediation_id=remediation_id,
            to_status="IN_PROGRESS",
            note="Viewer should not move remediation state.",
            operator_paths=paths,
            now="2026-03-19T12:00:00Z",
            today="2026-03-19",
        )
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass
