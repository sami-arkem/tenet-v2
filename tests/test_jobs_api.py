from __future__ import annotations

import base64
import time

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_manifest():
    return {
        "company_profile": {
            "company_name": "Acme Fintech",
            "industry": "fintech",
            "primary_jurisdiction": "uk",
            "additional_jurisdictions": ["eu"],
            "products": ["payments"],
            "entities": ["Acme Fintech Ltd"],
        },
        "scope": {
            "audit_id": "audit_001",
            "audit_type": "aml_readiness_review",
            "framework_ids": ["UK_MLR"],
            "domain": "aml",
            "domains": ["aml"],
            "jurisdictions": ["uk"],
            "in_scope_entities": ["Acme Fintech Ltd"],
            "in_scope_products": ["payments"],
            "evaluation_date": "2026-03-18",
            "historical_context_is_non_authoritative": True,
            "deterministic_current_audit_truth_only": True,
        },
        "controls": [],
        "evidence_catalog": [],
    }


def wait_for_job(job_id: str, timeout: float = 6.0):
    started = time.time()
    while time.time() - started < timeout:
        response = client.get(f"/v1/jobs/{job_id}")
        assert response.status_code == 200
        row = response.json()["data"]
        if row["status"] in {"SUCCEEDED", "FAILED"}:
            return row
        time.sleep(0.05)
    raise AssertionError(f"job did not finish in time: {job_id}")


def test_jobs_api_evidence_processing_flow():
    pack_response = client.post(
        "/v1/evidence-packs",
        json={
            "name": "Acme AML Pack",
            "created_by": "sami",
            "manifest": make_manifest(),
        },
    )
    assert pack_response.status_code == 200
    pack_id = pack_response.json()["data"]["pack_id"]

    upload_response = client.post(
        f"/v1/evidence-packs/{pack_id}/evidence/upload",
        json={
            "filename": "monitoring_policy.txt",
            "title": "Monitoring Policy",
            "source_type": "policy_document",
            "citation": "monitoring_policy.txt#L1-L1",
            "content_base64": base64.b64encode(
                b"Transaction monitoring policy for AML controls.\n"
            ).decode("ascii"),
        },
    )
    assert upload_response.status_code == 200

    submit_response = client.post(
        "/v1/jobs",
        json={
            "job_type": "process_evidence_pack",
            "payload": {"pack_id": pack_id},
        },
    )
    assert submit_response.status_code == 200
    job_id = submit_response.json()["data"]["job_id"]

    finished = wait_for_job(job_id)
    assert finished["status"] == "SUCCEEDED"
    assert finished["result"]["readiness"]["corpus_ready"] is True

    list_response = client.get("/v1/jobs")
    assert list_response.status_code == 200
    assert any(row["job_id"] == job_id for row in list_response.json()["data"]["items"])
