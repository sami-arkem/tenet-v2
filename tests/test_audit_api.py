from __future__ import annotations

from fastapi.testclient import TestClient

from api.audit_api import app


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


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "deterministic"


def test_execute_audit_success():
    response = client.post("/v1/audits/execute", json={"payload": make_payload()})
    assert response.status_code == 200

    body = response.json()
    assert body["topline"]["run_id"] == "run_aml_001"
    assert body["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"
    assert body["snapshot"]["readiness_label"] == "REMEDIATION_REQUIRED"
    assert body["report_bundle"]["deployment_decision"] == "CONDITIONALLY_APPROVED"
    assert "Tenet Deterministic Audit Report" in body["report_bundle"]["markdown"]


def test_execute_audit_validation_error():
    bad_payload = make_payload()
    bad_payload["scope"]["domains"] = []

    response = client.post("/v1/audits/execute", json={"payload": bad_payload})
    assert response.status_code == 400
    assert "domains" in response.json()["detail"]
