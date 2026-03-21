from __future__ import annotations

import json
from pathlib import Path

from core.export_package import export_audit_package


def make_payload():
    return {
        "run_id": "run_export_dossier_001",
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
                    "required_evidence_types": ["policy_document"],
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
            "questions": [],
        },
        "control_coverage_matrix": {
            "run_id": "run_export_dossier_001",
            "deterministic_authoritative": True,
            "summary": {"control_count": 1, "supported_controls": 1, "partial_controls": 0, "blocked_controls": 0},
            "controls": [],
        },
        "audit_dossier": {
            "run_id": "run_export_dossier_001",
            "deterministic_authoritative": True,
            "controls": [],
        },
    }


def test_export_package_writes_audit_dossier(tmp_path):
    out = export_audit_package(
        payload=make_payload(),
        export_root=tmp_path,
        package_name="run_export_dossier_001_package",
    )
    package_dir = Path(out["package_paths"]["package_dir"])
    assert (package_dir / "audit_dossier.json").exists()

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["audit_dossier_present"] is True
