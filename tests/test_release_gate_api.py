from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def make_payload():
    return {
        "run_id": "run_release_gate_api_001",
        "company_profile": {
            "company_name": "Acme Fintech",
            "industry": "fintech",
            "primary_jurisdiction": "uk",
            "additional_jurisdictions": [],
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
                    "description": "Policy must exist.",
                    "test_procedure": "Check policy.",
                    "required_evidence_types": ["policy_document"],
                    "severity_if_missing": "HIGH",
                },
                "provided_evidence": [
                    {
                        "evidence_id": "ev_001",
                        "title": "Monitoring Policy",
                        "source_type": "policy_document",
                        "file_path": "evidence/policy.pdf",
                        "citation": "policy.pdf#L1-L2",
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
                            "score": 2.5,
                            "excerpt": "transaction monitoring policy",
                        }
                    ],
                }
            ],
        },
    }


def test_release_gate_api_flow():
    create_response = client.post(
        "/v1/audits",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "package_name": "pkg_release_gate_api_001",
            },
        },
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["data"]["run_id"]

    coverage_response = client.post(f"/v1/control-coverage/audits/{run_id}/build")
    assert coverage_response.status_code == 200

    dossier_response = client.post(f"/v1/audit-dossier/audits/{run_id}/build")
    assert dossier_response.status_code == 200

    review_response = client.post(
        f"/v1/audits/{run_id}/review",
        json={
            "reviewer": "sami",
            "decision": "APPROVED",
            "rationale": "Deterministic package verified and approved.",
            "conditions": [],
            "evidence_refs": ["report.md", "audit_dossier.json"],
        },
    )
    assert review_response.status_code == 200

    build_response = client.post(f"/v1/release-gate/audits/{run_id}/build")
    assert build_response.status_code == 200
    data = build_response.json()["data"]
    assert data["release_ready"] is True
    assert data["release_status"] == "RELEASE_READY"

    get_response = client.get(f"/v1/release-gate/audits/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["run_id"] == run_id

    markdown_response = client.get(f"/v1/release-gate/audits/{run_id}/markdown")
    assert markdown_response.status_code == 200
    assert "RELEASE_READY" in markdown_response.json()["data"]["markdown"]
