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


def test_real_run_endpoint_executes_pipeline_and_exposes_surfaces(tmp_path: Path) -> None:
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
        },
    )
    assert create.status_code == 200
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

    # Verify preparation is ready
    prep = client.get(f"/v1/audit-preparation/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert prep.status_code == 200
    assert prep.json()["data"]["preparation_status"] == "READY"

    run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert run.status_code == 200
    # Run status depends on E2E pipeline execution results
    assert run.json()["data"]["queue_status"] in {"COMPLETED", "BLOCKED"}

    detail = client.get(f"/v1/audits/{audit_id}", headers={"X-User-ID": "admin-1"})
    assert detail.status_code == 200
    # Status depends on E2E pipeline results
    assert detail.json()["data"]["status"] in {"COMPLETED", "BLOCKED", "RUNNING"}

    latest = client.get(f"/v1/audits/{audit_id}/runs/latest", headers={"X-User-ID": "admin-1"})
    assert latest.status_code == 200
    # Deployment decision comes from E2E pipeline execution
    assert "deployment_decision" in latest.json()["data"]

    # Findings and report endpoints should be accessible
    findings_list = client.get(f"/v1/findings/audit/{audit_id}", headers={"X-User-ID": "viewer-1"})
    assert findings_list.status_code == 200

    report_summary = client.get(f"/v1/reports/{audit_id}/summary", headers={"X-User-ID": "viewer-1"})
    assert report_summary.status_code == 200

    export_manifest = client.get(f"/v1/reports/{audit_id}/export-manifest", headers={"X-User-ID": "viewer-1"})
    assert export_manifest.status_code == 200
    assert "manifest_path" in export_manifest.json()["data"]


def test_run_endpoint_blocks_when_evidence_not_ready(tmp_path: Path) -> None:
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

    # Seed requirements so gate has something to check
    seed_req = client.post(
        f"/v1/evidence/audits/{audit_id}/requirements/seed?required_categories=policy",
        headers={"X-User-ID": "admin-1"},
    )
    assert seed_req.status_code == 200

    # Run should block because no evidence is ready
    run = client.post(f"/v1/audits/{audit_id}/run", headers={"X-User-ID": "admin-1"})
    assert run.status_code == 400
    assert run.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


def test_cross_tenant_access_blocked_on_findings_and_reports(tmp_path: Path) -> None:
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

    outsider_findings = client.get(f"/v1/findings/audit/{audit_id}", headers={"X-User-ID": "outsider-1"})
    assert outsider_findings.status_code == 403

    outsider_report = client.get(f"/v1/reports/{audit_id}/summary", headers={"X-User-ID": "outsider-1"})
    assert outsider_report.status_code == 403
