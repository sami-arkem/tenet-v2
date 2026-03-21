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


def test_create_finalize_and_process_upload_session_end_to_end(tmp_path: Path) -> None:
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

    seed_req = client.post(
        f"/v1/evidence/audits/{audit_id}/requirements/seed",
        headers={"X-User-ID": "admin-1"},
        params=[("required_categories", "policy")],
    )
    assert seed_req.status_code == 200

    content = "control_id,description\nAML-01,Board oversight required\n"
    temp_file = tmp_path / "incoming" / "policy.csv"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

    session = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "policy.csv",
            "content_type": "text/csv",
            "sha256": sha,
            "byte_size": len(content.encode("utf-8")),
            "evidence_category": "policy",
        },
    )
    assert session.status_code == 200
    upload_session_id = session.json()["data"]["upload_session_id"]

    finalize = client.post(
        f"/v1/upload-sessions/{upload_session_id}/finalize",
        headers={"X-User-ID": "admin-1"},
        json={"temp_file_path": str(temp_file)},
    )
    assert finalize.status_code == 200
    evidence_id = finalize.json()["data"]["evidence_id"]
    assert evidence_id

    jobs = client.get("/v1/evidence-jobs", headers={"X-User-ID": "viewer-1"})
    assert jobs.status_code == 200
    assert jobs.json()["data"]["total_queued"] == 1

    worker = client.post("/v1/evidence-jobs/run-next", headers={"X-User-ID": "admin-1"})
    assert worker.status_code == 200
    assert worker.json()["data"]["status"] == "COMPLETED"

    evidence_detail = client.get(f"/v1/evidence/{evidence_id}", headers={"X-User-ID": "viewer-1"})
    assert evidence_detail.status_code == 200
    assert evidence_detail.json()["data"]["status"] == "READY"

    gate = client.post(
        f"/v1/evidence/audits/{audit_id}/gate/recompute",
        headers={"X-User-ID": "admin-1"},
    )
    assert gate.status_code == 200
    assert gate.json()["data"]["gate_status"] == "PASS"

    blob_manifest_dir = Path(os.environ["TENET_STATE_DIR"]) / "blob_store" / "manifests"
    manifests = list(blob_manifest_dir.glob("*.json"))
    assert len(manifests) == 1


def test_finalize_blocks_checksum_mismatch(tmp_path: Path) -> None:
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

    content = "wrong file"
    temp_file = tmp_path / "incoming" / "bad.csv"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text(content, encoding="utf-8")

    session = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": audit_id,
            "filename": "bad.csv",
            "content_type": "text/csv",
            "sha256": "0" * 64,
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
    assert finalize.status_code == 400


def test_upload_session_tenant_isolation(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create = client.post(
        "/v1/upload-sessions",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_id": "audit-1",
            "filename": "policy.csv",
            "content_type": "text/csv",
            "sha256": "a" * 64,
            "byte_size": 10,
            "evidence_category": "policy",
        },
    )
    upload_session_id = create.json()["data"]["upload_session_id"]

    outsider = client.post(
        f"/v1/upload-sessions/{upload_session_id}/cancel",
        headers={"X-User-ID": "outsider-1"},
        json={},
    )
    assert outsider.status_code == 403
