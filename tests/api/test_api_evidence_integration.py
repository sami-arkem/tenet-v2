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
            "analyst-1": {"tenant_id": "tenant-b", "role": "ANALYST"},
            "viewer-1": {"tenant_id": "tenant-b", "role": "VIEWER"},
            "outsider-1": {"tenant_id": "tenant-x", "role": "ADMIN"},
        }
    })

    os.environ["TENET_ACTOR_DIRECTORY_PATH"] = str(actor_directory_path)
    os.environ["TENET_STATE_DIR"] = str(state_dir)

    return TestClient(create_app())


def test_register_complete_ready_and_list_evidence(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    register = client.post(
        "/v1/evidence/register",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": "audit-1",
            "filename": "policy.pdf",
            "content_type": "application/pdf",
            "sha256": "a" * 64,
            "byte_size": 1200,
            "evidence_category": "policy",
            "note": "Initial upload",
        },
    )
    assert register.status_code == 200
    evidence_id = register.json()["data"]["evidence_id"]

    complete = client.post(
        f"/v1/evidence/{evidence_id}/complete",
        headers={"X-User-ID": "admin-1"},
        json={"storage_path": "/bucket/policy.pdf", "processing_started": True},
    )
    assert complete.status_code == 200
    assert complete.json()["data"]["status"] == "PROCESSING"

    ready = client.post(
        f"/v1/evidence/{evidence_id}/mark-ready",
        headers={"X-User-ID": "admin-1"},
        json={"extracted_text_ready": True, "inventory_ready": True},
    )
    assert ready.status_code == 200
    assert ready.json()["data"]["status"] == "READY"

    listing = client.get("/v1/evidence?audit_id=audit-1", headers={"X-User-ID": "viewer-1"})
    assert listing.status_code == 200
    assert listing.json()["data"]["total_ready"] == 1

    detail = client.get(f"/v1/evidence/{evidence_id}", headers={"X-User-ID": "viewer-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["immutable_after_ready"] is True


def test_duplicate_detection_and_immutability(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    body = {
        "audit_id": "audit-1",
        "filename": "policy.pdf",
        "content_type": "application/pdf",
        "sha256": "b" * 64,
        "byte_size": 1200,
        "evidence_category": "policy",
    }

    first = client.post("/v1/evidence/register", headers={"X-User-ID": "admin-1"}, json=body)
    assert first.status_code == 200
    evidence_id = first.json()["data"]["evidence_id"]

    duplicate = client.post("/v1/evidence/register", headers={"X-User-ID": "admin-1"}, json=body)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["error"]["code"] == "EVIDENCE_DUPLICATE"

    client.post(
        f"/v1/evidence/{evidence_id}/complete",
        headers={"X-User-ID": "admin-1"},
        json={"storage_path": "/bucket/policy.pdf", "processing_started": True},
    )
    client.post(
        f"/v1/evidence/{evidence_id}/mark-ready",
        headers={"X-User-ID": "admin-1"},
        json={"extracted_text_ready": True, "inventory_ready": True},
    )

    mutate = client.post(
        f"/v1/evidence/{evidence_id}/fail",
        headers={"X-User-ID": "admin-1"},
        json={"error_message": "should fail"},
    )
    assert mutate.status_code == 400
    assert mutate.json()["detail"]["error"]["code"] == "EVIDENCE_IMMUTABLE"


def test_gate_recompute_and_audit_run_enforce_real_evidence_lifecycle(tmp_path: Path) -> None:
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
    assert create_audit.status_code == 200
    audit_id = create_audit.json()["data"]["audit_id"]

    # Ensure audit preparation requirements
    ensure = client.post(f"/v1/audit-preparation/{audit_id}/requirements/ensure", headers={"X-User-ID": "admin-1"})
    assert ensure.status_code == 200

    # Check preparation is blocked initially
    prep_empty = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert prep_empty.status_code == 200
    assert prep_empty.json()["data"]["preparation_status"] == "BLOCKED"

    # Run should be blocked
    blocked_run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert blocked_run.status_code == 400

    # Upload and process evidence for policy
    content1 = "AML policy board governance control framework"
    temp_file1 = tmp_path / "incoming" / "policy.csv"
    temp_file1.parent.mkdir(parents=True, exist_ok=True)
    temp_file1.write_text(content1, encoding="utf-8")
    sha1 = hashlib.sha256(content1.encode("utf-8")).hexdigest()

    session1 = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "policy.csv",
            "content_type": "text/csv",
            "sha256": sha1,
            "byte_size": len(content1.encode("utf-8")),
            "evidence_category": "policy",
        },
    )
    upload_session_id1 = session1.json()["data"]["upload_session_id"]
    finalize1 = client.post(
        f"/v1/upload-sessions/{upload_session_id1}/finalize",
        headers={"X-User-ID": "admin-1"},
        json={"temp_file_path": str(temp_file1)},
    )
    assert finalize1.status_code == 200
    worker1 = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
    assert worker1.status_code == 200

    # Check preparation - still blocked because governance is missing
    prep_partial = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert prep_partial.status_code == 200
    assert prep_partial.json()["data"]["preparation_status"] == "BLOCKED"

    # Upload and process evidence for governance
    content2 = "board committee governance minutes oversight escalation"
    temp_file2 = tmp_path / "incoming" / "governance.csv"
    temp_file2.parent.mkdir(parents=True, exist_ok=True)
    temp_file2.write_text(content2, encoding="utf-8")
    sha2 = hashlib.sha256(content2.encode("utf-8")).hexdigest()

    session2 = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "governance.csv",
            "content_type": "text/csv",
            "sha256": sha2,
            "byte_size": len(content2.encode("utf-8")),
            "evidence_category": "governance",
        },
    )
    upload_session_id2 = session2.json()["data"]["upload_session_id"]
    finalize2 = client.post(
        f"/v1/upload-sessions/{upload_session_id2}/finalize",
        headers={"X-User-ID": "admin-1"},
        json={"temp_file_path": str(temp_file2)},
    )
    assert finalize2.status_code == 200
    worker2 = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
    assert worker2.status_code == 200

    # Upload and process evidence for risk_assessment
    content3 = "risk assessment inherent risk residual risk control effectiveness"
    temp_file3 = tmp_path / "incoming" / "risk.csv"
    temp_file3.parent.mkdir(parents=True, exist_ok=True)
    temp_file3.write_text(content3, encoding="utf-8")
    sha3 = hashlib.sha256(content3.encode("utf-8")).hexdigest()

    session3 = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "risk.csv",
            "content_type": "text/csv",
            "sha256": sha3,
            "byte_size": len(content3.encode("utf-8")),
            "evidence_category": "risk_assessment",
        },
    )
    upload_session_id3 = session3.json()["data"]["upload_session_id"]
    finalize3 = client.post(
        f"/v1/upload-sessions/{upload_session_id3}/finalize",
        headers={"X-User-ID": "admin-1"},
        json={"temp_file_path": str(temp_file3)},
    )
    assert finalize3.status_code == 200
    worker3 = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
    assert worker3.status_code == 200

    # Check preparation - should be ready now
    prep_ready = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert prep_ready.status_code == 200
    assert prep_ready.json()["data"]["preparation_status"] == "READY"

    # Now run should succeed
    good_run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert good_run.status_code == 200


def test_cross_tenant_blocked_on_evidence_detail(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    register = client.post(
        "/v1/evidence/register",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": "audit-1",
            "filename": "policy.pdf",
            "content_type": "application/pdf",
            "sha256": "e" * 64,
            "byte_size": 1200,
            "evidence_category": "policy",
        },
    )
    evidence_id = register.json()["data"]["evidence_id"]

    outsider = client.get(f"/v1/evidence/{evidence_id}", headers={"X-User-ID": "outsider-1"})
    assert outsider.status_code == 403
