from __future__ import annotations

from api.store import execute_and_store_audit
from core.audit_dossier_service import build_audit_dossier
from core.control_coverage_service import build_control_coverage_matrix
from core.release_gate_service import (
    build_release_gate,
    get_release_gate,
    render_release_gate_markdown,
)
from core.review_service import submit_review_decision


def make_payload():
    return {
        "run_id": "run_release_gate_001",
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


def test_release_gate_ready(tmp_path):
    execute_and_store_audit(
        payload=make_payload(),
        export={"create_export_package": True, "package_name": "pkg_001"},
        store_root=tmp_path,
    )
    build_control_coverage_matrix(run_id="run_release_gate_001", audit_root=tmp_path)
    build_audit_dossier(run_id="run_release_gate_001", audit_root=tmp_path)
    submit_review_decision(
        run_id="run_release_gate_001",
        reviewer="sami",
        decision="APPROVED",
        rationale="Deterministic package verified and approved.",
        conditions=[],
        evidence_refs=["report.md", "audit_dossier.json"],
        store_root=tmp_path,
    )

    gate = build_release_gate(run_id="run_release_gate_001", audit_root=tmp_path)
    assert gate["release_ready"] is True
    assert gate["release_status"] == "RELEASE_READY"

    loaded = get_release_gate(run_id="run_release_gate_001", audit_root=tmp_path)
    assert loaded["run_id"] == "run_release_gate_001"

    markdown = render_release_gate_markdown(run_id="run_release_gate_001", audit_root=tmp_path)
    assert "Release status: RELEASE_READY" in markdown


def test_release_gate_blocked_without_review(tmp_path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)
    build_control_coverage_matrix(run_id="run_release_gate_001", audit_root=tmp_path)
    build_audit_dossier(run_id="run_release_gate_001", audit_root=tmp_path)

    gate = build_release_gate(run_id="run_release_gate_001", audit_root=tmp_path)
    assert gate["release_ready"] is False
    assert "review_state_missing" in gate["reasons_blocking_release"]
