from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_payload():
    return {
        "run_id": "run_aml_001",
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
                "notes": "Policy exists but monitoring evidence is incomplete.",
            }
        ],
        "default_remediation_owner": "compliance@acme.com",
        "prior_historical_context": {"prior_findings": 2},
        "metadata": {"source": "unit_test"},
    }


def test_remediation_endpoints():
    create_response = client.post("/v1/audits", json={"payload": make_payload()})
    assert create_response.status_code == 200
    run_id = create_response.json()["data"]["run_id"]

    list_response = client.get(f"/v1/audits/{run_id}/remediations")
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    remediation_id = items[0]["remediation_id"]

    get_response = client.get(f"/v1/audits/{run_id}/remediations/{remediation_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "OPEN"

    patch_response = client.patch(
        f"/v1/audits/{run_id}/remediations/{remediation_id}",
        json={
            "owner": "owner@acme.com",
            "status": "IN_REMEDIATION",
            "note": "Started work on monitoring remediation.",
            "evidence_links": ["evidence/remediation_plan.pdf"],
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()["data"]
    assert updated["owner"] == "owner@acme.com"
    assert updated["status"] == "IN_REMEDIATION"
    assert updated["evidence_links"] == ["evidence/remediation_plan.pdf"]
    assert len(updated["comment_history"]) == 1


def test_remediation_not_found():
    response = client.get("/v1/audits/does_not_exist/remediations")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "HTTP_404"
