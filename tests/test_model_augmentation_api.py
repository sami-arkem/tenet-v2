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


def make_audit_payload():
    return {
        "run_id": "run_model_api_001",
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
        "controls": [
            {
                "control": {
                    "control_id": "AML.MONITORING.001",
                    "regime_id": "UK_MLR.001",
                    "title": "Transaction monitoring policy",
                    "description": "A documented transaction monitoring control must exist.",
                    "test_procedure": "Check for policy and monitoring evidence.",
                    "required_evidence_types": ["policy_document", "monitoring_report"],
                    "severity_if_missing": "HIGH",
                },
                "provided_evidence": [
                    {
                        "evidence_id": "ev_001",
                        "title": "Monitoring Policy",
                        "source_type": "policy_document",
                        "file_path": "evidence/policy.pdf",
                        "citation": "policy.pdf#L1-L20",
                    }
                ],
                "declared_control_present": True,
                "declared_operating_effective": True,
            }
        ],
        "default_remediation_owner": "compliance@acme.com",
    }


def test_model_augmentation_api_flow():
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
            "filename": "policy.txt",
            "title": "Monitoring Policy",
            "source_type": "policy_document",
            "citation": "policy.txt#L1-L1",
            "content_base64": base64.b64encode(
                b"AML policy and procedure for transaction monitoring."
            ).decode("ascii"),
        },
    )
    assert upload_response.status_code == 200
    evidence_id = upload_response.json()["data"]["evidence_id"]

    process_response = client.post(f"/v1/evidence-packs/{pack_id}/processing/items/{evidence_id}")
    assert process_response.status_code == 200

    augment_item = client.post(f"/v1/model-augmentation/evidence-packs/{pack_id}/items/{evidence_id}")
    assert augment_item.status_code == 200
    assert augment_item.json()["data"]["non_authoritative"] is True

    augment_pack = client.post(f"/v1/model-augmentation/evidence-packs/{pack_id}/run")
    assert augment_pack.status_code == 200
    assert augment_pack.json()["data"]["augmented_count"] >= 1

    audit_response = client.post("/v1/audits", json={"payload": make_audit_payload()})
    assert audit_response.status_code == 200
    run_id = audit_response.json()["data"]["run_id"]

    augment_report = client.post(f"/v1/model-augmentation/audits/{run_id}/report")
    assert augment_report.status_code == 200
    assert augment_report.json()["data"]["non_authoritative"] is True

    get_report = client.get(f"/v1/model-augmentation/audits/{run_id}/report")
    assert get_report.status_code == 200
    assert get_report.json()["data"]["run_id"] == run_id
