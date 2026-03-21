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
        "prior_historical_context": {"prior_findings": 2},
        "metadata": {"source": "unit_test"},
    }


def test_evidence_pack_flow():
    create_response = client.post(
        "/v1/evidence-packs",
        json={
            "name": "Acme AML Pack",
            "created_by": "sami",
            "manifest": make_manifest(),
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    pack_id = created["pack_id"]

    list_response = client.get("/v1/evidence-packs")
    assert list_response.status_code == 200
    assert any(row["pack_id"] == pack_id for row in list_response.json()["data"]["items"])

    get_response = client.get(f"/v1/evidence-packs/{pack_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["detail"]["pack_id"] == pack_id

    blocked_response = client.post(
        f"/v1/evidence-packs/{pack_id}/execute",
        json={
            "run_id": "run_aml_from_pack_001",
            "default_remediation_owner": "compliance@acme.com",
            "metadata": {"executed_from": "api_test"},
        },
    )
    assert blocked_response.status_code == 400

    upload_response = client.post(
        f"/v1/evidence-packs/{pack_id}/evidence/upload",
        json={
            "filename": "monitoring_policy.txt",
            "title": "Monitoring Policy",
            "source_type": "policy_document",
            "citation": "monitoring_policy.txt#L1-L1",
            "content_base64": base64.b64encode(
                b"Transaction monitoring policy and alert escalation controls.\n"
            ).decode("ascii"),
        },
    )
    assert upload_response.status_code == 200

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/run")
    assert process_response.status_code == 200
    assert process_response.json()["data"]["readiness"]["corpus_ready"] is True

    execute_response = client.post(
        f"/v1/evidence-packs/{pack_id}/execute",
        json={
            "run_id": "run_aml_from_pack_001",
            "default_remediation_owner": "compliance@acme.com",
            "metadata": {"executed_from": "api_test"},
        },
    )
    assert execute_response.status_code == 200
    execution = execute_response.json()["data"]["execution"]
    assert execution["run_id"] == "run_aml_from_pack_001"
    assert execution["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"


def test_evidence_pack_not_found():
    response = client.get("/v1/evidence-packs/does_not_exist")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "HTTP_404"
