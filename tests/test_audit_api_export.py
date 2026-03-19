from __future__ import annotations

from pathlib import Path

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


def test_execute_audit_without_export():
    response = client.post("/v1/audits/execute", json={"payload": make_payload()})
    assert response.status_code == 200

    body = response.json()
    assert body["topline"]["run_id"] == "run_aml_001"
    assert body["export_package"] is None
    assert body["snapshot"]["readiness_label"] == "REMEDIATION_REQUIRED"


def test_execute_audit_with_export(tmp_path: Path):
    export_root = Path("artifacts") / "test_audit_api_export"
    response = client.post(
        "/v1/audits/execute",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "export_root": str(export_root),
                "package_name": "run_aml_001_package",
                "package_version": "v1",
            },
        },
    )
    assert response.status_code == 200

    body = response.json()
    export_package = body["export_package"]
    assert export_package is not None
    assert export_package["run_id"] == "run_aml_001"
    assert export_package["verification"]["all_ok"] is True
    assert export_package["manifest"]["generated_from_canonical_runtime"] is True
    assert export_package["manifest"]["historical_context_is_non_authoritative"] is True
    assert export_package["manifest"]["deterministic_current_audit_truth_only"] is True

    package_dir = Path(export_package["package_paths"]["package_dir"])
    assert package_dir.exists()
    assert (package_dir / "report.md").exists()
    assert (package_dir / "manifest.json").exists()


def test_execute_audit_with_invalid_export_root():
    response = client.post(
        "/v1/audits/execute",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "export_root": "../bad",
            },
        },
    )
    assert response.status_code == 400
    assert "parent traversal" in response.json()["detail"]


def test_execute_audit_with_absolute_export_root():
    response = client.post(
        "/v1/audits/execute",
        json={
            "payload": make_payload(),
            "export": {
                "create_export_package": True,
                "export_root": "/tmp/bad",
            },
        },
    )
    assert response.status_code == 400
    assert "relative path" in response.json()["detail"]
