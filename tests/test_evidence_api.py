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


def test_evidence_upload_and_list():
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
            "content_base64": base64.b64encode(b"real policy text\n").decode("ascii"),
        },
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()["data"]
    assert uploaded["processing_status"] == "UPLOADED"
    assert uploaded["detected_mime"] == "text/plain"

    list_response = client.get(f"/v1/evidence-packs/{pack_id}/evidence")
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["evidence_id"] == uploaded["evidence_id"]


def test_evidence_upload_rejects_bad_extension():
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
            "filename": "malware.exe",
            "title": "Bad File",
            "source_type": "unknown",
            "citation": "malware.exe#L1-L1",
            "content_base64": base64.b64encode(b"abc").decode("ascii"),
        },
    )
    assert upload_response.status_code == 400
    assert upload_response.json()["error"]["code"] == "HTTP_400"
