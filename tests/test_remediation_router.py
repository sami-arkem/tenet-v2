from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.remediation import router
from core.remediation_operator_service import RemediationOperatorPaths, bootstrap_from_generated_remediation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _seed(tmp_path: Path) -> tuple[TestClient, str]:
    base = tmp_path / "state"
    generated = base / "remediation" / "generated_items.jsonl"
    actor_dir = {
        "admin-1": {"tenant_id": "tenant-b", "role": "ADMIN"},
        "owner-1": {"tenant_id": "tenant-b", "role": "OWNER"},
        "analyst-1": {"tenant_id": "tenant-b", "role": "ANALYST"},
        "viewer-1": {"tenant_id": "tenant-b", "role": "VIEWER"},
    }
    generated_rows = [
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
    _write_jsonl(generated, generated_rows)

    paths = RemediationOperatorPaths(
        items=str(base / "remediation" / "remediation_items_operator.jsonl"),
        timeline=str(base / "remediation" / "remediation_timeline.jsonl"),
        lifecycle_index=str(base / "remediation" / "remediation_lifecycle_index.json"),
        gate=str(base / "remediation" / "remediation_gate.json"),
        evidence_metadata=str(base / "remediation" / "remediation_evidence_metadata.jsonl"),
        notification_outbox=str(base / "remediation" / "remediation_notification_outbox.jsonl"),
        operator_audit_log=str(base / "remediation" / "remediation_operator_audit_log.jsonl"),
    )
    bootstrap_from_generated_remediation(
        generated_items_path=generated,
        operator_paths=paths,
        now="2026-03-19T10:00:00Z",
        today="2026-03-19",
    )

    app = FastAPI()
    app.include_router(router, prefix="/v1/remediation", tags=["remediation"])
    app.state.actor_directory = actor_dir

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.user_id = request.headers.get("x-user-id")
        request.state.tenant_id = actor_dir[request.state.user_id]["tenant_id"] if request.state.user_id in actor_dir else None
        request.state.user_role = actor_dir[request.state.user_id]["role"] if request.state.user_id in actor_dir else None
        return await call_next(request)

    import os
    os.environ["TENET_STATE_DIR"] = str(base)

    return TestClient(app), generated_rows[0]["remediation_id"]


def test_list_dashboard_and_detail(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    rows = client.get("/v1/remediation", headers={"x-user-id": "viewer-1"})
    assert rows.status_code == 200
    assert len(rows.json()["data"]) == 1

    dashboard = client.get("/v1/remediation/dashboard?today=2026-03-19", headers={"x-user-id": "viewer-1"})
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["open_count"] == 1

    detail = client.get(f"/v1/remediation/{remediation_id}", headers={"x-user-id": "viewer-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["remediation"]["remediation_id"] == remediation_id


def test_assign_owner_and_status_flow(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    assign = client.post(
        f"/v1/remediation/{remediation_id}/assign-owner",
        headers={"x-user-id": "admin-1"},
        json={"owner_user_id": "analyst-1", "note": "Assigning this item to the analyst for follow-up."},
    )
    assert assign.status_code == 200

    due_date = client.post(
        f"/v1/remediation/{remediation_id}/due-date",
        headers={"x-user-id": "owner-1"},
        json={"due_date": "2026-03-25", "note": "Setting a due date ahead of the next review cycle."},
    )
    assert due_date.status_code == 200

    move = client.post(
        f"/v1/remediation/{remediation_id}/status",
        headers={"x-user-id": "analyst-1"},
        json={"to_status": "IN_PROGRESS", "note": "Starting remediation work and gathering evidence now.", "evidence_files": []},
    )
    assert move.status_code == 200

    evidence_submit = client.post(
        f"/v1/remediation/{remediation_id}/status",
        headers={"x-user-id": "analyst-1"},
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
        headers={"x-user-id": "owner-1"},
        json={"verification_passed": True, "updated_gap_note": None},
    )
    assert verify.status_code == 200

    detail = client.get(f"/v1/remediation/{remediation_id}", headers={"x-user-id": "viewer-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["remediation"]["status"] == "CLOSED"


def test_plan_due_notifications(tmp_path: Path) -> None:
    client, remediation_id = _seed(tmp_path)

    assign = client.post(
        f"/v1/remediation/{remediation_id}/assign-owner",
        headers={"x-user-id": "admin-1"},
        json={"owner_user_id": "analyst-1", "note": "Assigning this item to the analyst for follow-up."},
    )
    assert assign.status_code == 200

    due_date = client.post(
        f"/v1/remediation/{remediation_id}/due-date",
        headers={"x-user-id": "owner-1"},
        json={"due_date": "2026-03-20", "note": "Setting a due date ahead of the next review cycle."},
    )
    assert due_date.status_code == 200

    planned = client.post(
        "/v1/remediation/jobs/plan-due-notifications?today=2026-03-19&now=2026-03-19T09:00:00Z",
        headers={"x-user-id": "admin-1"},
    )
    assert planned.status_code == 200
    assert planned.json()["data"]["planned_events"] == 1
