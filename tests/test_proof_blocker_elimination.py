from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_blocker_elimination.py")
    spec = importlib.util.spec_from_file_location("proof_blocker_elimination", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_audit_context_semantics_ok(tmp_path: Path):
    module = load_module()
    audit_context = tmp_path / "audit_context.json"
    audit_context.write_text(json.dumps({
        "audit_id": "aml_eu_case_001",
        "entity_name": "AML EU case 001",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["eu"],
        "domains": ["aml"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5,
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
        "operator_fill_status": {
            "real_sources_attached": True,
            "placeholder_free": True,
            "ready_for_import": True,
        },
    }), encoding="utf-8")

    plan_item = module.PlanItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    errors = module.validate_audit_context_semantics(path=audit_context, plan_item=plan_item)
    assert errors == []


def test_validate_expected_assertions_semantics_ok(tmp_path: Path):
    module = load_module()
    path = tmp_path / "expected_assertions.json"
    path.write_text(json.dumps({
        "case_id": "aml_eu_case_001",
        "expected": {
            "equals": {"deployment_decision.status": "BLOCKED"},
            "contains": {"missing_controls": ["AML-001"]},
            "minimums": {"control_assessment.control_coverage_score": 0.2}
        },
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True
        }
    }), encoding="utf-8")

    plan_item = module.PlanItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    errors = module.validate_expected_assertions_semantics(path=path, plan_item=plan_item)
    assert errors == []


def test_validate_expected_assertions_semantics_blocks_bad_shape(tmp_path: Path):
    module = load_module()
    path = tmp_path / "expected_assertions.json"
    path.write_text(json.dumps({
        "case_id": "bad id",
        "expected": {
            "equals": {"": ""},
            "contains": {"missing_controls": []},
            "minimums": {"coverage score": "high"},
        },
        "rules": {
            "no_invented_pass_outcome": False,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": False
        },
        "extra": True,
    }), encoding="utf-8")

    plan_item = module.PlanItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    errors = module.validate_expected_assertions_semantics(path=path, plan_item=plan_item)
    assert any("case_id_mismatch" in e for e in errors)
    assert any("unexpected_keys" in e for e in errors)
    assert any("no_invented_pass_outcome_must_be_true" in e for e in errors)
    assert any("historical_context_cannot_override_current_truth_must_be_true" in e for e in errors)
    assert any("equals_invalid_key" in e or "equals_empty_value" in e for e in errors)
    assert any("contains_invalid_list" in e for e in errors)
    assert any("minimums_invalid_numeric" in e for e in errors)


def test_validate_item_collects_semantic_issues(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "wrong_id",
        "entity_name": "Wrong Entity",
        "audit_type": "",
        "industry": "",
        "domains": ["fraud"],
        "jurisdictions": ["eu"],
        "source_families": [],
        "query_terms": [],
        "top_k": 0,
        "historical_context_is_non_authoritative": False,
        "deterministic_current_audit_truth_only": False,
        "operator_fill_status": {
            "real_sources_attached": False,
            "placeholder_free": False,
            "ready_for_import": False,
        },
    }), encoding="utf-8")

    (source_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "aml_eu_case_001",
        "expected": {
            "equals": {},
            "contains": {},
            "minimums": {},
        },
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True,
        },
    }), encoding="utf-8")

    (source_dir / "case_notes.md").write_text("TODO placeholder", encoding="utf-8")

    plan_item = module.PlanItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    result = module.validate_item(plan_item=plan_item, readiness_item=None)
    assert result["ready"] is False
    assert result["blocker_count"] > 0
    messages = [x["message"] for x in result["issues"]]
    assert any("domains_mismatch" in m for m in messages)
    assert any("audit_id_mismatch" in m for m in messages)
    assert any("no_meaningful_expected_values" in m for m in messages)
