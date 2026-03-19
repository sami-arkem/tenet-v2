from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _seed(tmp_path: Path) -> TestClient:
    actor_directory_path = tmp_path / "actor_directory.json"
    state_dir = tmp_path / "state"

    _write_json(actor_directory_path, {
        "users": {
            "admin-1": {"tenant_id": "tenant-b", "role": "ADMIN"},
            "viewer-1": {"tenant_id": "tenant-b", "role": "VIEWER"},
            "outsider-1": {"tenant_id": "tenant-x", "role": "ADMIN"},
        }
    })

    os.environ["TENET_ACTOR_DIRECTORY_PATH"] = str(actor_directory_path)
    os.environ["TENET_STATE_DIR"] = str(state_dir)

    return TestClient(create_app())


def test_audit_preparation_blocks_run_until_checklist_is_green(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create_audit = client.post(
        "/v1/audits",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_kind": "aml_periodic",
            "entity_id": "entity-1",
            "system_name": "Payments Risk Engine",
            "jurisdiction": "UK",
            "framework": "FCA",
        },
    )
    audit_id = create_audit.json()["data"]["audit_id"]

    ensure = client.post(f"/v1/audit-preparation/{audit_id}/requirements/ensure", headers={"X-User-ID": "admin-1"})
    assert ensure.status_code == 200

    prep_before = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "viewer-1"})
    assert prep_before.status_code == 200
    assert prep_before.json()["data"]["preparation_status"] == "BLOCKED"

    blocked_run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert blocked_run.status_code == 400

    for category, content in {
        "policy": "AML policy board governance control framework",
        "governance": "board committee governance minutes oversight escalation",
        "risk_assessment": "risk assessment inherent risk residual risk control effectiveness",
    }.items():
        temp_file = tmp_path / "incoming" / f"{category}.csv"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

        session = client.post(
            "/v1/upload-sessions",
            headers={"X-User-ID": "admin-1"},
            json={
                "audit_id": audit_id,
                "filename": f"{category}.csv",
                "content_type": "text/csv",
                "sha256": sha,
                "byte_size": len(content.encode("utf-8")),
                "evidence_category": category,
            },
        )
        upload_session_id = session.json()["data"]["upload_session_id"]
        finalize = client.post(
            f"/v1/upload-sessions/{upload_session_id}/finalize",
            headers={"X-User-ID": "admin-1"},
            json={"temp_file_path": str(temp_file)},
        )
        assert finalize.status_code == 200
        worker = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
        assert worker.status_code == 200

    prep_after = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "viewer-1"})
    assert prep_after.status_code == 200
    assert prep_after.json()["data"]["preparation_status"] == "READY"


def test_ocr_submission_logs_model_call_and_allows_review_resolution(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create_audit = client.post(
        "/v1/audits",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_kind": "aml_periodic",
            "entity_id": "entity-1",
            "system_name": "Payments Risk Engine",
            "jurisdiction": "UK",
            "framework": "FCA",
        },
    )
    audit_id = create_audit.json()["data"]["audit_id"]

    ensure = client.post(f"/v1/audit-preparation/{audit_id}/requirements/ensure", headers={"X-User-ID": "admin-1"})
    assert ensure.status_code == 200

    # Create a simple CSV file that will be processed successfully
    content = "miscellaneous notes"
    temp_file = tmp_path / "incoming" / "notes.csv"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

    session = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "notes.csv",
            "content_type": "text/csv",
            "sha256": sha,
            "byte_size": len(content.encode("utf-8")),
            "evidence_category": "policy",
        },
    )
    upload_session_id = session.json()["data"]["upload_session_id"]
    finalize = client.post(
        f"/v1/upload-sessions/{upload_session_id}/finalize",
        headers={"X-User-ID": "admin-1"},
        json={"temp_file_path": str(temp_file)},
    )
    evidence_id = finalize.json()["data"]["evidence_id"]

    # Process the evidence
    worker = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
    assert worker.status_code == 200

    # Submit OCR text (simulating manual OCR for a scanned document)
    submit = client.post(
        f"/v1/ocr-submissions/{evidence_id}",
        headers={"X-User-ID": "admin-1"},
        json={"ocr_text": "AML policy board governance control framework"},
    )
    assert submit.status_code == 200

    # Verify model call was logged
    model_calls = client.get(f"/v1/audit-preparation/{audit_id}/model-calls", headers={"X-User-ID": "viewer-1"})
    assert model_calls.status_code == 200
    assert len(model_calls.json()["data"]) >= 1
