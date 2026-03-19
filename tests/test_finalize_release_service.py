from __future__ import annotations

import json
from pathlib import Path

from api.store import execute_and_store_audit
from core.audit_dossier_service import build_audit_dossier
from core.control_coverage_service import build_control_coverage_matrix
from core.finalize_release_service import (
    finalize_released_audit,
    get_release_finalization,
    render_release_finalization_markdown,
)
from core.review_service import submit_review_decision


def make_payload():
    return {
        "run_id": "run_finalize_001",
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
        "composed_report_bundle": {
            "run_id": "run_finalize_001",
            "markdown": "# Composed Report\n\nThis is the composed report.\n",
            "deterministic_authoritative": True,
            "model_augmentation_present": False,
            "overall_posture": "GREEN",
            "deployment_decision": "APPROVED",
            "finding_count": 0,
            "remediation_count": 0,
        },
    }


def test_finalize_released_audit(tmp_path):
    execute_and_store_audit(
        payload=make_payload(),
        export={"create_export_package": True, "package_name": "initial_pkg"},
        store_root=tmp_path,
    )
    build_control_coverage_matrix(run_id="run_finalize_001", audit_root=tmp_path)
    build_audit_dossier(run_id="run_finalize_001", audit_root=tmp_path)
    submit_review_decision(
        run_id="run_finalize_001",
        reviewer="sami",
        decision="APPROVED",
        rationale="Approved for release.",
        conditions=[],
        evidence_refs=["report.md", "audit_dossier.json"],
        store_root=tmp_path,
    )

    payload = finalize_released_audit(
        run_id="run_finalize_001",
        release_root=tmp_path / "released",
        package_name="released_pkg_001",
        audit_root=tmp_path,
    )
    assert payload["release_ready"] is True
    assert payload["release_status"] == "FINALIZED"
    assert payload["released_package"]["verification"]["all_ok"] is True
    assert payload["composed_report_summary"]["report_source"] == "composed_report_bundle"

    package_dir = Path(payload["released_package"]["package_paths"]["package_dir"])
    report_md = (package_dir / "report.md").read_text(encoding="utf-8")
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "Composed Report" in report_md
    assert manifest["report_source"] == "composed_report_bundle"

    loaded = get_release_finalization(run_id="run_finalize_001", audit_root=tmp_path)
    assert loaded["run_id"] == "run_finalize_001"

    markdown = render_release_finalization_markdown(run_id="run_finalize_001", audit_root=tmp_path)
    assert "Report source: composed_report_bundle" in markdown


def test_finalize_blocks_when_not_release_ready(tmp_path):
    execute_and_store_audit(payload=make_payload(), store_root=tmp_path)
    build_control_coverage_matrix(run_id="run_finalize_001", audit_root=tmp_path)
    build_audit_dossier(run_id="run_finalize_001", audit_root=tmp_path)

    try:
        finalize_released_audit(
            run_id="run_finalize_001",
            release_root=tmp_path / "released",
            package_name="released_pkg_001",
            audit_root=tmp_path,
        )
    except ValueError as exc:
        assert "not release ready" in str(exc)
    else:
        raise AssertionError("expected finalization to fail")
