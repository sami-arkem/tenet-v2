from __future__ import annotations

import base64

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
            "framework_ids": ["UK_MLR", "EU_AMLD6"],
            "domain": "aml",
            "domains": ["aml"],
            "jurisdictions": ["uk", "eu"],
            "in_scope_entities": ["Acme Fintech Ltd"],
            "in_scope_products": ["payments"],
            "evaluation_date": "2026-03-18",
            "historical_context_is_non_authoritative": True,
            "deterministic_current_audit_truth_only": True,
        },
        "controls": [],
        "evidence_catalog": [],
    }


def test_workflow_api_flow():
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

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/run")
    assert process_response.status_code == 200
    assert process_response.json()["data"]["readiness"]["corpus_ready"] is True

    wf_create = client.post(
        "/v1/workflows",
        json={
            "pack_id": pack_id,
            "created_by": "sami",
        },
    )
    assert wf_create.status_code == 200
    workflow_id = wf_create.json()["data"]["workflow_id"]

    wf_readiness = client.post(f"/v1/workflows/{workflow_id}/readiness")
    assert wf_readiness.status_code == 200
    assert wf_readiness.json()["data"]["status"] == "READY_FOR_EXECUTION"

    wf_execute = client.post(
        f"/v1/workflows/{workflow_id}/execute",
        json={
            "run_id": "run_workflow_api_001",
            "default_remediation_owner": "compliance@acme.com",
        },
    )
    assert wf_execute.status_code == 200
    assert wf_execute.json()["data"]["status"] == "AUDIT_EXECUTED"

    wf_rem = client.post(f"/v1/workflows/{workflow_id}/remediation")
    assert wf_rem.status_code == 200
    assert wf_rem.json()["data"]["status"] == "REMEDIATION_ACTIVE"
    assert wf_rem.json()["data"]["latest_remediation_summary"]["item_count"] >= 1

    wf_get = client.get(f"/v1/workflows/{workflow_id}")
    assert wf_get.status_code == 200
    assert len(wf_get.json()["data"]["timeline"]) >= 4

    wf_list = client.get("/v1/workflows")
    assert wf_list.status_code == 200
    assert any(row["workflow_id"] == workflow_id for row in wf_list.json()["data"]["items"])
