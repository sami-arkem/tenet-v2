from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_payload():
    return {
        "run_id": "run_composed_api_001",
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


def test_composed_reports_api_flow():
    audit_response = client.post("/v1/audits", json={"payload": make_payload()})
    assert audit_response.status_code == 200
    run_id = audit_response.json()["data"]["run_id"]

    augment_response = client.post(f"/v1/model-augmentation/audits/{run_id}/report")
    assert augment_response.status_code == 200

    payload_response = client.get(f"/v1/composed-reports/{run_id}/payload")
    assert payload_response.status_code == 200
    payload = payload_response.json()["data"]
    assert payload["deterministic_authoritative"] is True
    assert payload["model_augmentation"]["present"] is True

    markdown_response = client.get(f"/v1/composed-reports/{run_id}/markdown")
    assert markdown_response.status_code == 200
    markdown = markdown_response.json()["data"]["markdown"]
    assert "Deterministic Findings" in markdown
    assert "Model-Augmented Executive Narrative" in markdown
