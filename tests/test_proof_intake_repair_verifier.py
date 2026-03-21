from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_intake_repair_verifier.py")
    spec = importlib.util.spec_from_file_location("proof_intake_repair_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_audit_context_ok(tmp_path: Path):
    module = load_module()
    path = tmp_path / "audit_context.json"
    path.write_text(json.dumps({
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
        "entity_name": "Acme Bank",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "source_families": ["aml", "regulations"],
        "query_terms": ["aml monitoring"],
        "top_k": 5,
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "operator_fill_status": {
            "real_sources_attached": True,
            "placeholder_free": True,
            "ready_for_import": True,
        },
    }), encoding="utf-8")
    issues = module.validate_audit_context(path, ["aml"], ["eu"])
    assert issues == []


def test_validate_expected_assertions_ok(tmp_path: Path):
    module = load_module()
    path = tmp_path / "expected_assertions.json"
    path.write_text(json.dumps({
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True,
        },
        "expected_assertions": [
            {
                "assertion_id": "assertion_001",
                "type": "finding",
                "control_id": "AML.MONITORING.001",
                "regime_id": "EU.AMLD6.001",
                "expected_value": "missing_alert_escalation_control",
                "evidence_refs": ["procedures/aml.md#L10-L20"],
            }
        ],
    }), encoding="utf-8")
    issues = module.validate_expected_assertions(path)
    assert issues == []


def test_validate_operator_claims_detects_mismatch(tmp_path: Path):
    module = load_module()
    source_dir = tmp_path / "item"
    source_dir.mkdir()
    (source_dir / "audit_context.json").write_text("{}", encoding="utf-8")
    entry = {
        "required_files": ["audit_context.json"],
        "operator_repair": {
            "files_present": {"audit_context.json": False},
            "placeholders_removed": True,
            "evidence_refs": ["x"],
        },
    }
    issues = module.validate_operator_claims(entry, source_dir)
    assert any("file_exists_but_not_confirmed" in issue for issue in issues)


def test_verify_entry_ready_gold_case(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(json.dumps({
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
        "entity_name": "Acme Bank",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "source_families": ["aml", "regulations"],
        "query_terms": ["aml monitoring"],
        "top_k": 5,
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "operator_fill_status": {
            "real_sources_attached": True,
            "placeholder_free": True,
            "ready_for_import": True,
        },
    }), encoding="utf-8")

    (source_dir / "expected_assertions.json").write_text(json.dumps({
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True,
        },
        "expected_assertions": [
            {
                "assertion_id": "assertion_001",
                "type": "finding",
                "control_id": "AML.MONITORING.001",
                "regime_id": "EU.AMLD6.001",
                "expected_value": "missing_alert_escalation_control",
                "evidence_refs": ["procedures/aml.md#L10-L20"],
            }
        ],
    }), encoding="utf-8")

    (source_dir / "case_notes.md").write_text(
        "Real source-grounded notes describing deterministic expected findings in enough detail.",
        encoding="utf-8",
    )

    entry = {
        "id": "aml_eu_case_001",
        "kind": "gold_case",
        "title": "AML EU case 001",
        "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
        "operator_repair": {
            "completed": True,
            "files_present": {
                "audit_context.json": True,
                "expected_assertions.json": True,
                "case_notes.md": True,
            },
            "audit_context_checked": True,
            "expected_assertions_checked": True,
            "case_notes_checked": True,
            "placeholders_removed": True,
            "evidence_refs": ["intake/proof_batch_real_002/aml_eu_case_001/audit_context.json"],
        },
    }
    report = module.verify_entry(entry)
    assert report["verified_ready"] is True
    assert report["issue_count"] == 0


def test_compile_verified_manifest():
    module = load_module()
    report = {
        "entries": [
            {
                "kind": "gold_case",
                "id": "aml_eu_case_001",
                "title": "AML EU case 001",
                "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
                "domains": ["aml"],
                "jurisdictions": ["eu"],
                "verified_ready": True,
            },
            {
                "kind": "customer_pack",
                "id": "aml_us_pack_001",
                "title": "AML US pack 001",
                "source_dir": "intake/proof_batch_real_002/aml_us_pack_001",
                "domains": ["aml"],
                "jurisdictions": ["us"],
                "verified_ready": False,
            },
        ]
    }
    manifest = module.compile_verified_manifest(report)
    assert len(manifest["items"]) == 1
    assert manifest["items"][0]["id"] == "aml_eu_case_001"
