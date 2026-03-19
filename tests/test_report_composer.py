from __future__ import annotations

from api.store import execute_and_store_audit
from core.model_augmentation_service import augment_audit_report_with_models
from core.report_composer import (
    build_composed_report_bundle,
    build_composed_report_payload,
    render_composed_markdown_report,
)


def make_payload():
    return {
        "run_id": "run_composed_001",
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


def test_composed_report_without_augmentation(tmp_path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)

    payload = build_composed_report_payload(run_id="run_composed_001", audit_root=tmp_path)
    assert payload["deterministic_authoritative"] is True
    assert payload["model_augmentation"]["present"] is False

    markdown = render_composed_markdown_report(run_id="run_composed_001", audit_root=tmp_path)
    assert "Deterministic Findings" in markdown
    assert "Authority Boundary" in markdown


def test_composed_report_with_augmentation(tmp_path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)
    augment_audit_report_with_models(run_id="run_composed_001", audit_root=tmp_path)

    bundle = build_composed_report_bundle(run_id="run_composed_001", audit_root=tmp_path)
    assert bundle["deterministic_authoritative"] is True
    assert bundle["model_augmentation_present"] is True
    assert "Model-Augmented Executive Narrative" in bundle["markdown"]
