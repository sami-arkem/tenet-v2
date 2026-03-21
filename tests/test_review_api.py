from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_payload():
    return {
        "run_id": "run_aml_review_api_001",
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
            }
        ],
        "default_remediation_owner": "compliance@acme.com",
    }


def test_review_api_flow():
    create_response = client.post(
        "/v1/audits",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "package_name": "run_aml_review_api_001_package",
            },
        },
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["data"]["run_id"]

    get_seeded = client.get(f"/v1/audits/{run_id}/review")
    assert get_seeded.status_code == 200
    assert get_seeded.json()["data"]["status"] == "PENDING_REVIEW"

    submit = client.post(
        f"/v1/audits/{run_id}/review",
        json={
            "reviewer": "sami",
            "decision": "CONDITIONALLY_APPROVED",
            "rationale": "Evidence is mostly sufficient but remediation must close before deployment.",
            "conditions": ["Close monitoring evidence gap."],
            "evidence_refs": ["report.md", "report_pack.json"],
            "note": "Reviewed against export package.",
        },
    )
    assert submit.status_code == 200
    data = submit.json()["data"]
    assert data["status"] == "REVIEWED"
    assert data["conditionally_approved"] is True
    assert data["review_count"] == 1
    assert data["latest_review"]["reviewer"] == "sami"


def test_review_requires_conditions_for_conditional():
    create_response = client.post("/v1/audits", json={"payload": make_payload()})
    assert create_response.status_code == 200
    run_id = create_response.json()["data"]["run_id"]

    submit = client.post(
        f"/v1/audits/{run_id}/review",
        json={
            "reviewer": "sami",
            "decision": "CONDITIONALLY_APPROVED",
            "rationale": "Need more work.",
            "conditions": [],
            "evidence_refs": [],
        },
    )
    assert submit.status_code == 400
    assert submit.json()["error"]["code"] == "HTTP_400"
