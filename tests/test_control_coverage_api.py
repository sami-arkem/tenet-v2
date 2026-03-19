from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_payload():
    return {
        "run_id": "run_cov_api_001",
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
        "audit_context_pack": {
            "deterministic_authoritative": True,
            "question_count": 1,
            "selected_chunk_count": 1,
            "questions": [
                {
                    "question": "What evidence supports AML.MONITORING.001?",
                    "matches": [
                        {
                            "chunk_id": "ev_001::chunk_0000",
                            "evidence_id": "ev_001",
                            "filename": "policy.txt",
                            "title": "Monitoring Policy",
                            "source_type": "policy_document",
                            "score": 3.2,
                            "excerpt": "AML transaction monitoring policy",
                        }
                    ],
                }
            ],
        },
    }


def test_control_coverage_api_flow():
    create_response = client.post("/v1/audits", json={"payload": make_payload()})
    assert create_response.status_code == 200
    run_id = create_response.json()["data"]["run_id"]

    build_response = client.post(f"/v1/control-coverage/audits/{run_id}/build")
    assert build_response.status_code == 200
    data = build_response.json()["data"]
    assert data["deterministic_authoritative"] is True
    assert data["summary"]["control_count"] == 1
    assert data["summary"]["partial_controls"] == 1

    get_response = client.get(f"/v1/control-coverage/audits/{run_id}")
    assert get_response.status_code == 200
    row = get_response.json()["data"]["controls"][0]
    assert row["control_id"] == "AML.MONITORING.001"
    assert row["missing_required_evidence_types"] == ["monitoring_report"]
