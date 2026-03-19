from __future__ import annotations

from core.audit_pipeline import (
    build_execution_bundle,
    derive_readiness_label,
    result_to_snapshot,
    run_audit_from_payload,
)
from core.report_renderer import render_markdown_report


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


def test_run_audit_from_payload():
    result = run_audit_from_payload(make_payload())
    assert result.run_id == "run_aml_001"
    assert result.summary.control_count == 1
    assert len(result.findings) == 1
    assert result.summary.deployment_decision.value == "CONDITIONALLY_APPROVED"


def test_build_execution_bundle():
    bundle = build_execution_bundle(make_payload())
    assert bundle["topline"]["run_id"] == "run_aml_001"
    assert bundle["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"
    assert bundle["topline"]["finding_count"] == 1
    assert "report_pack" in bundle
    assert "deterministic_audit_result" in bundle


def test_result_snapshot_and_readiness():
    result = run_audit_from_payload(make_payload())
    snapshot = result_to_snapshot(result)
    readiness = derive_readiness_label(result)
    assert readiness == "REMEDIATION_REQUIRED"
    assert snapshot["summary"]["deployment_decision"] == "CONDITIONALLY_APPROVED"
    assert snapshot["finding_counts"]["HIGH"] == 1


def test_render_markdown_report():
    result = run_audit_from_payload(make_payload())
    markdown = render_markdown_report(result)
    assert "# Tenet Deterministic Audit Report: run_aml_001" in markdown
    assert "Historical context is included only as prior context" in markdown
    assert "### AML.MONITORING.001 (UK_MLR.001)" in markdown
    assert "### remediation::0001" in markdown
