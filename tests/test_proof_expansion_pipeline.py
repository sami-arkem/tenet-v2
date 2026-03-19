from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_expansion_pipeline.py")
    spec = importlib.util.spec_from_file_location("proof_expansion_pipeline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_gold_case_contract(tmp_path: Path):
    module = load_module()
    case_dir = tmp_path / "aml_us_case_001"
    case_dir.mkdir()
    (case_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "audit-001",
        "entity_name": "Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "domains": ["aml", "governance"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")
    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "aml_us_case_001",
        "expected": {"equals": {"deployment_decision.status": "BLOCKED"}}
    }), encoding="utf-8")
    (case_dir / "case_notes.md").write_text("notes", encoding="utf-8")
    config = {
        "allowed_domains": ["aml", "governance"],
        "allowed_jurisdictions": ["us"],
    }

    result = module.validate_item(
        kind="gold_case",
        source_dir=case_dir,
        item_id="aml_us_case_001",
        expected_domains=["aml", "governance"],
        expected_jurisdictions=["us"],
        config=config,
    )
    assert result["domains"] == ["aml", "governance"]
    assert result["jurisdictions"] == ["us"]


def test_validate_customer_pack_contract(tmp_path: Path):
    module = load_module()
    pack_dir = tmp_path / "aml_us_pack_001"
    pack_dir.mkdir()
    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml-us-pack-001",
        "entity_name": "Pack Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "domains": ["aml", "governance"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")
    config = {
        "allowed_domains": ["aml", "governance"],
        "allowed_jurisdictions": ["us"],
    }

    result = module.validate_item(
        kind="customer_pack",
        source_dir=pack_dir,
        item_id="aml_us_pack_001",
        expected_domains=["aml", "governance"],
        expected_jurisdictions=["us"],
        config=config,
    )
    assert result["domains"] == ["aml", "governance"]
    assert result["jurisdictions"] == ["us"]


def test_validate_customer_pack_contract_rejects_domain_mismatch(tmp_path: Path):
    module = load_module()
    pack_dir = tmp_path / "aml_us_pack_001"
    pack_dir.mkdir()
    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml_us_pack_001",
        "entity_name": "Pack Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "domains": ["aml"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")
    config = {
        "allowed_domains": ["aml", "governance"],
        "allowed_jurisdictions": ["us"],
    }

    try:
        module.validate_item(
            kind="customer_pack",
            source_dir=pack_dir,
            item_id="aml_us_pack_001",
            expected_domains=["aml", "governance"],
            expected_jurisdictions=["us"],
            config=config,
        )
    except ValueError as exc:
        assert "domains mismatch" in str(exc)
    else:
        raise AssertionError("Expected domain mismatch to fail")


def test_validate_item_accepts_nested_taxonomy_config(tmp_path: Path):
    module = load_module()
    pack_dir = tmp_path / "aml_us_pack_001"
    pack_dir.mkdir()
    (pack_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "aml_us_pack_001",
        "entity_name": "Pack Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "domains": ["aml", "governance"],
        "source_families": ["regulations", "aml"],
        "query_terms": ["aml policy"],
        "top_k": 5
    }), encoding="utf-8")
    config = {
        "taxonomy": {
            "domains": ["aml", "governance"],
            "jurisdictions": ["us"]
        }
    }

    result = module.validate_item(
        kind="customer_pack",
        source_dir=pack_dir,
        item_id="aml_us_pack_001",
        expected_domains=["aml", "governance"],
        expected_jurisdictions=["us"],
        config=config,
    )
    assert result["domains"] == ["aml", "governance"]


def test_load_plan_recommendations_reads_proof_density_output(tmp_path: Path, monkeypatch):
    module = load_module()
    logs_dir = tmp_path / "logs" / "proof_density"
    logs_dir.mkdir(parents=True)
    (logs_dir / "proof_density_status.json").write_text(json.dumps({
        "gold_cases": {
            "gap_plan": {
                "actual_total": 52,
                "target_total": 100,
                "remaining_to_target": 48,
                "recommended_next_batch": [
                    {"domain": "aml", "jurisdiction": "canada", "reason": "zero_coverage"},
                    {"domain": "fraud", "jurisdiction": "eu", "reason": "zero_coverage"}
                ]
            }
        },
        "customer_packs": {
            "gap_plan": {
                "actual_total": 6,
                "target_total": 20,
                "remaining_to_target": 14,
                "recommended_next_batch": [
                    {"domain": "aml", "jurisdiction": "australia", "reason": "zero_coverage"}
                ]
            }
        }
    }), encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)

    plan = module.load_plan_recommendations("gold_case", 1)
    assert plan["actual_total"] == 52
    assert plan["recommended_next_batch"] == [
        {"domain": "aml", "jurisdiction": "canada", "reason": "zero_coverage"}
    ]
