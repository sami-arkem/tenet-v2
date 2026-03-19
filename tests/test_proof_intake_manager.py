from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_intake_manager.py")
    spec = importlib.util.spec_from_file_location("proof_intake_manager", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_planned_items_from_plan():
    module = load_module()
    plan = {
        "batch_label": "proof_batch_real_002",
        "items": [
            {
                "kind": "gold_case",
                "id": "aml_eu_case_001",
                "title": "AML EU case 001",
                "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
                "domains": ["aml"],
                "jurisdictions": ["eu"],
                "reason": "zero_coverage"
            }
        ]
    }
    items = module.planned_items_from_plan(plan)
    assert len(items) == 1
    assert items[0].item_id == "aml_eu_case_001"
    assert items[0].domains == ["aml"]
    assert items[0].jurisdictions == ["eu"]


def test_materialize_workspace(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    item = module.PlannedItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    out = module.materialize_workspace(item, overwrite=False)
    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"

    assert out["materialized"] is True
    assert (source_dir / "README.md").exists()
    assert (source_dir / "audit_context.json").exists()
    assert (source_dir / "expected_assertions.json").exists()
    assert (source_dir / "case_notes.md").exists()
    assert (source_dir / "notes.md").exists()


def test_compute_item_readiness_ready_gold_case(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml_eu_case_001",
        "entity_name": "AML EU case 001",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["eu"],
        "domains": ["aml"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")

    (source_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "aml_eu_case_001",
        "expected": {
            "equals": {"deployment_decision.status": "BLOCKED"},
            "contains": {},
            "minimums": {}
        }
    }), encoding="utf-8")

    (source_dir / "case_notes.md").write_text(
        "# Case\n\nReal source grounded notes.\n",
        encoding="utf-8",
    )

    item = module.PlannedItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    readiness = module.compute_item_readiness(item)
    assert readiness["ready"] is True
    assert readiness["missing_required"] == []
    assert readiness["validation_errors"] == []
    assert readiness["placeholder_findings"] == []


def test_compute_item_readiness_blocks_placeholders(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml_eu_case_001",
        "entity_name": "AML EU case 001",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["eu"],
        "domains": ["aml"],
        "source_families": ["TODO"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")

    (source_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "aml_eu_case_001",
        "expected": {
            "equals": {"deployment_decision.status": "TODO"},
            "contains": {},
            "minimums": {}
        }
    }), encoding="utf-8")

    (source_dir / "case_notes.md").write_text(
        "# TODO\n\nplaceholder\n",
        encoding="utf-8",
    )

    item = module.PlannedItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    readiness = module.compute_item_readiness(item)
    assert readiness["ready"] is False
    assert readiness["placeholder_findings"]


def test_validate_audit_context_mismatch(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml_eu_case_001",
        "entity_name": "AML EU case 001",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "domains": ["fraud"],
        "jurisdictions": ["eu"],
        "source_families": ["regulations"],
        "query_terms": ["policy"],
        "top_k": 5
    }), encoding="utf-8")

    item = module.PlannedItem(
        kind="gold_case",
        item_id="aml_eu_case_001",
        title="AML EU case 001",
        source_dir="intake/proof_batch_real_002/aml_eu_case_001",
        domains=["aml"],
        jurisdictions=["eu"],
        reason="zero_coverage",
    )

    errors = module.validate_audit_context(source_dir / "audit_context.json", item)
    assert any("domains_mismatch" in e for e in errors)
