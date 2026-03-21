from __future__ import annotations

from pathlib import Path

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


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["service"] == "tenet-api"


def test_create_get_report_and_list():
    create_response = client.post(
        "/v1/audits",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "export_root": str(Path("artifacts") / "api_test_packages"),
                "package_name": "run_aml_001_package",
                "package_version": "v1",
            },
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    run_id = created["run_id"]
    assert created["snapshot"]["readiness_label"] == "REMEDIATION_REQUIRED"
    assert created["export_package"] is not None

    get_response = client.get(f"/v1/audits/{run_id}")
    assert get_response.status_code == 200
    detail = get_response.json()["data"]
    assert detail["run_id"] == run_id
    assert detail["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"

    report_response = client.get(f"/v1/audits/{run_id}/report")
    assert report_response.status_code == 200
    report = report_response.json()["data"]
    assert report["run_id"] == run_id
    assert "Tenet Deterministic Audit Report" in report["markdown"]

    list_response = client.get("/v1/audits")
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert any(row["run_id"] == run_id for row in items)


def test_not_found_returns_envelope():
    response = client.get("/v1/audits/does_not_exist")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "HTTP_404"


def test_invalid_payload_returns_envelope():
    payload = make_payload()
    payload["scope"]["domains"] = []

    response = client.post("/v1/audits", json={"payload": payload})
    assert response.status_code == 400
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "HTTP_400"
