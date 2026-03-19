from __future__ import annotations

from pathlib import Path

from api.store import execute_and_store_audit
from core.control_coverage_service import (
    build_control_coverage_matrix,
    get_control_coverage_matrix,
)


def make_payload():
    return {
        "run_id": "run_cov_001",
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
            "question_count": 2,
            "selected_chunk_count": 2,
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


def test_build_and_get_control_coverage_matrix(tmp_path: Path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)

    payload = build_control_coverage_matrix(run_id="run_cov_001", audit_root=tmp_path)
    assert payload["deterministic_authoritative"] is True
    assert payload["summary"]["control_count"] == 1
    assert payload["summary"]["partial_controls"] == 1

    row = payload["controls"][0]
    assert row["control_id"] == "AML.MONITORING.001"
    assert row["coverage_status"] == "PARTIAL"
    assert row["covered_evidence_types"] == ["policy_document"]
    assert row["missing_required_evidence_types"] == ["monitoring_report"]
    assert len(row["context_matches"]) == 1

    loaded = get_control_coverage_matrix(run_id="run_cov_001", audit_root=tmp_path)
    assert loaded["run_id"] == "run_cov_001"
