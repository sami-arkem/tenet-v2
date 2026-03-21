from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app
from core.remediation_operator_service import RemediationOperatorPaths, bootstrap_from_generated_remediation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _seed(tmp_path: Path) -> tuple[TestClient, str]:
    actor_directory_path = tmp_path / "actor_directory.json"
    state_dir = tmp_path / "state"
    generated_items = state_dir / "remediation" / "generated_items.jsonl"

    _write_json(actor_directory_path, {
        "users": {
            "admin-1": {"tenant_id": "tenant-b", "role": "ADMIN"},
            "owner-1": {"tenant_id": "tenant-b", "role": "OWNER"},
            "analyst-1": {"tenant_id": "tenant-b", "role": "ANALYST"},
            "viewer-1": {"tenant_id": "tenant-b", "role": "VIEWER"},
            "outsider-1": {"tenant_id": "tenant-x", "role": "ADMIN"},
        }
    })

    _write_jsonl(generated_items, [{
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
    }])

    bootstrap_from_generated_remediation(
        generated_items_path=generated_items,
        operator_paths=RemediationOperatorPaths(
            items=str(state_dir / "remediation" / "remediation_items_operator.jsonl"),
            timeline=str(state_dir / "remediation" / "remediation_timeline.jsonl"),
            lifecycle_index=str(state_dir / "remediation" / "remediation_lifecycle_index.json"),
            gate=str(state_dir / "remediation" / "remediation_gate.json"),
            evidence_metadata=str(state_dir / "remediation" / "remediation_evidence_metadata.jsonl"),
            notification_outbox=str(state_dir / "remediation" / "remediation_notification_outbox.jsonl"),
            operator_audit_log=str(state_dir / "remediation" / "remediation_operator_audit_log.jsonl"),
        ),
        now="2026-03-19T10:00:00Z",
        today="2026-03-19",
    )

    os.environ["TENET_ACTOR_DIRECTORY_PATH"] = str(actor_directory_path)
    os.environ["TENET_STATE_DIR"] = str(state_dir)

    return TestClient(create_app()), "tenant-b:vendor_risk_review:audit-1:reason:deterministic_decision:blocked"


def test_auth_required(tmp_path: Path) -> None:
    client, _ = _seed(tmp_path)
    response = client.get("/v1/remediation")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_list_dashboard_detail_and_role_enforcement(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    rows = client.get("/v1/remediation", headers={"X-User-ID": "viewer-1"})
    assert rows.status_code == 200
    assert len(rows.json()["data"]) == 1

    dashboard = client.get("/v1/remediation/dashboard?today=2026-03-19", headers={"X-User-ID": "viewer-1"})
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["open_count"] == 1

    detail = client.get(f"/v1/remediation/{remediation_id}", headers={"X-User-ID": "viewer-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["remediation"]["remediation_id"] == remediation_id

    forbidden = client.post(
        f"/v1/remediation/{remediation_id}/assign-owner",
        headers={"X-User-ID": "viewer-1"},
        json={"owner_user_id": "analyst-1", "note": "Viewer should not be allowed to assign ownership."},
    )
    assert forbidden.status_code == 403


def test_full_remediation_route_flow(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    assign = client.post(
        f"/v1/remediation/{remediation_id}/assign-owner",
        headers={"X-User-ID": "admin-1"},
        json={"owner_user_id": "analyst-1", "note": "Assigning this item to the analyst for follow-up."},
    )
    assert assign.status_code == 200

    due_date = client.post(
        f"/v1/remediation/{remediation_id}/due-date",
        headers={"X-User-ID": "owner-1"},
        json={"due_date": "2026-03-20", "note": "Setting a due date ahead of the next review cycle."},
    )
    assert due_date.status_code == 200

    move = client.post(
        f"/v1/remediation/{remediation_id}/status",
        headers={"X-User-ID": "analyst-1"},
        json={"to_status": "IN_PROGRESS", "note": "Starting remediation work and gathering evidence now.", "evidence_files": []},
    )
    assert move.status_code == 200

    evidence_submit = client.post(
        f"/v1/remediation/{remediation_id}/status",
        headers={"X-User-ID": "analyst-1"},
        json={
            "to_status": "EVIDENCE_SUBMITTED",
            "note": "Submitting remediation evidence for verification now.",
            "evidence_files": [
                {"file_id": "file-1", "filename": "policy-v2.pdf", "content_type": "application/pdf", "sha256": "abc123", "byte_size": 1200}
            ],
        },
    )
    assert evidence_submit.status_code == 200

    verify = client.post(
        f"/v1/remediation/{remediation_id}/verification-result",
        headers={"X-User-ID": "owner-1"},
        json={"verification_passed": True, "updated_gap_note": None},
    )
    assert verify.status_code == 200

    detail = client.get(f"/v1/remediation/{remediation_id}", headers={"X-User-ID": "viewer-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["remediation"]["status"] == "CLOSED"


def test_due_notification_job_route(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    assign = client.post(
        f"/v1/remediation/{remediation_id}/assign-owner",
        headers={"X-User-ID": "admin-1"},
        json={"owner_user_id": "analyst-1", "note": "Assigning this item to the analyst for follow-up."},
    )
    assert assign.status_code == 200

    due_date = client.post(
        f"/v1/remediation/{remediation_id}/due-date",
        headers={"X-User-ID": "owner-1"},
        json={"due_date": "2026-03-20", "note": "Setting a due date ahead of the next review cycle."},
    )
    assert due_date.status_code == 200

    planned = client.post(
        "/v1/remediation/jobs/plan-due-notifications?today=2026-03-19&now=2026-03-19T09:00:00Z",
        headers={"X-User-ID": "admin-1"},
    )
    assert planned.status_code == 200
    assert planned.json()["data"]["planned_events"] == 1
