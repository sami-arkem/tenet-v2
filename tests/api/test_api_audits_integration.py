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
            "outsider-1": {"tenant_id": "tenant-x", "role": "ADMIN"},
        }
    })

    os.environ["TENET_ACTOR_DIRECTORY_PATH"] = str(actor_directory_path)
    os.environ["TENET_STATE_DIR"] = str(state_dir)

    return TestClient(create_app())


def test_create_list_and_detail_audit(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create = client.post(
        "/v1/audits",
        headers={"X-User-ID": "admin-1"},
        json={
            "audit_kind": "aml_periodic",
            "entity_id": "entity-1",
            "system_name": "Payments Risk Engine",
            "jurisdiction": "UK",
            "framework": "FCA",
            "scheduled_date": "2026-03-25",
            "note": "First production audit.",
        },
    )
    assert create.status_code == 200
    audit_id = create.json()["data"]["audit_id"]

    listing = client.get("/v1/audits", headers={"X-User-ID": "admin-1"})
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = client.get(f"/v1/audits/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert detail.status_code == 200
    assert detail.json()["data"]["audit_id"] == audit_id


def test_trigger_run_then_sync_from_artifacts(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create = client.post(
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
    audit_id = create.json()["data"]["audit_id"]

    # Seed audit preparation requirements
    ensure = client.post(f"/v1/audit-preparation/{audit_id}/requirements/ensure", headers={"X-User-ID": "admin-1"})
    assert ensure.status_code == 200

    # Upload and process evidence for all required categories
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

    # Trigger the run - this executes the full E2E pipeline
    run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert run.status_code == 200

    # Release endpoint should be accessible
    release = client.get(f"/v1/audits/{audit_id}/release", headers={"X-User-ID": "admin-1"})
    assert release.status_code == 200


def test_tenant_isolation_on_audit_detail(tmp_path: Path) -> None:
    client = _seed(tmp_path)

    create = client.post(
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
    audit_id = create.json()["data"]["audit_id"]

    outsider = client.get(f"/v1/audits/{audit_id}", headers={"X-User-ID": "outsider-1"})
    assert outsider.status_code == 403
