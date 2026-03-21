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


def test_processing_api_flow():
    create_response = client.post(
        "/v1/evidence-packs",
        json={
            "name": "Acme AML Pack",
            "created_by": "sami",
            "manifest": make_manifest(),
        },
    )
    assert create_response.status_code == 200
    pack_id = create_response.json()["data"]["pack_id"]

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
    evidence_id = upload_response.json()["data"]["evidence_id"]

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/items/{evidence_id}")
    assert process_response.status_code == 200
    processed = process_response.json()["data"]
    assert processed["processing_status"] == "READY"
    assert processed["classification"]["confidence"] == "HIGH"

    readiness_response = client.get(f"/v1/evidence-packs/{pack_id}/processing/readiness")
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()["data"]
    assert readiness["corpus_ready"] is True
    assert readiness["event"] == "CORPUS_READY"


def test_bulk_processing_api_flow():
    create_response = client.post(
        "/v1/evidence-packs",
        json={
            "name": "Acme AML Pack 2",
            "created_by": "sami",
            "manifest": make_manifest(),
        },
    )
    assert create_response.status_code == 200
    pack_id = create_response.json()["data"]["pack_id"]

    for filename, title, source_type, content in [
        ("monitoring_policy.txt", "Monitoring Policy", "policy_document", b"Transaction monitoring policy.\n"),
        ("owner_matrix.json", "Owner Matrix", "owner_matrix", b'{"owner":"compliance"}'),
    ]:
        upload_response = client.post(
            f"/v1/evidence-packs/{pack_id}/evidence/upload",
            json={
                "filename": filename,
                "title": title,
                "source_type": source_type,
                "citation": f"{filename}#L1-L1",
                "content_base64": base64.b64encode(content).decode("ascii"),
            },
        )
        assert upload_response.status_code == 200

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/run")
    assert process_response.status_code == 200
    payload = process_response.json()["data"]
    assert payload["processed_count"] == 2
    assert payload["failure_count"] == 0
    assert payload["readiness"]["corpus_ready"] is True
