from __future__ import annotations

import json
from pathlib import Path

from core.export_package import (
    build_package_paths,
    export_audit_package,
    validate_export_manifest,
    verify_export_package,
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


def test_export_audit_package(tmp_path: Path):
    out = export_audit_package(
        payload=make_payload(),
        export_root=tmp_path,
        package_name="run_aml_001_package",
    )

    package_dir = Path(out["package_paths"]["package_dir"])
    assert package_dir.exists()
    assert (package_dir / "report.md").exists()
    assert (package_dir / "report_pack.json").exists()
    assert (package_dir / "deterministic_audit_result.json").exists()
    assert (package_dir / "manifest.json").exists()

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run_aml_001"
    assert manifest["generated_from_canonical_runtime"] is True
    assert manifest["historical_context_is_non_authoritative"] is True
    assert manifest["deterministic_current_audit_truth_only"] is True

    verification = out["verification"]
    assert verification["all_ok"] is True
    assert out["topline"]["deployment_decision"] == "CONDITIONALLY_APPROVED"


def test_verify_export_package_detects_tamper(tmp_path: Path):
    out = export_audit_package(
        payload=make_payload(),
        export_root=tmp_path,
        package_name="run_aml_001_package",
    )
    package_dir = Path(out["package_paths"]["package_dir"])
    report_md = package_dir / "report.md"
    report_md.write_text("tampered\n", encoding="utf-8")

    verification = verify_export_package(package_dir)
    assert verification["all_ok"] is False
    report_row = next(row for row in verification["files"] if row["path"] == "report.md")
    assert report_row["sha_ok"] is False


def test_validate_export_manifest_rejects_bad_flags():
    bad_manifest = {
        "package_version": "v1",
        "run_id": "run_001",
        "generated_from_canonical_runtime": False,
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
        "files": [
            {"path": "x.json", "sha256": "a" * 64, "size_bytes": 1}
        ],
    }
    try:
        validate_export_manifest(bad_manifest)
    except ValueError as exc:
        assert "generated_from_canonical_runtime" in str(exc)
    else:
        raise AssertionError("expected manifest validation to fail")


def test_build_package_paths_sanitizes_name(tmp_path: Path):
    paths = build_package_paths(tmp_path, "run aml 001 / package")
    assert paths.package_dir.name == "run_aml_001_package"
