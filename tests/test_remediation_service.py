from __future__ import annotations

from api.store import execute_and_store_audit
from core.remediation_service import (
    build_remediation_summary,
    get_remediation,
    list_remediations,
    update_remediation,
)


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


def test_remediation_state_seed_and_update(tmp_path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)

    items = list_remediations("run_aml_001", store_root=tmp_path)
    assert len(items) == 1
    remediation_id = items[0]["remediation_id"]

    updated = update_remediation(
        run_id="run_aml_001",
        remediation_id=remediation_id,
        owner="owner@acme.com",
        due_date="2026-04-01",
        status="IN_REMEDIATION",
        note="Owner assigned and remediation started.",
        evidence_links=["evidence/remediation_plan.pdf"],
        store_root=tmp_path,
    )
    assert updated["owner"] == "owner@acme.com"
    assert updated["status"] == "IN_REMEDIATION"
    assert len(updated["comment_history"]) == 1

    fetched = get_remediation("run_aml_001", remediation_id, store_root=tmp_path)
    assert fetched["owner"] == "owner@acme.com"
    assert fetched["evidence_links"] == ["evidence/remediation_plan.pdf"]

    summary = build_remediation_summary("run_aml_001", store_root=tmp_path)
    assert summary["item_count"] == 1
    assert summary["status_counts"]["IN_REMEDIATION"] == 1
