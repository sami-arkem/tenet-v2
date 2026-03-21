from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/build_proof_batch_plan.py")
    spec = importlib.util.spec_from_file_location("build_proof_batch_plan", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_batch_label():
    module = load_module()
    assert module.validate_batch_label("Proof Batch Real 002") == "proof_batch_real_002"


def test_build_ids():
    module = load_module()
    assert module.build_gold_id("aml", "eu", 3) == "aml_eu_case_003"
    assert module.build_pack_id("fraud", "canada", 2) == "fraud_canada_pack_002"


def test_build_plan_from_recommendations(tmp_path: Path, monkeypatch):
    module = load_module()
    status = {
        "gold_cases": {
            "gap_plan": {
                "recommended_next_batch": [
                    {"domain": "aml", "jurisdiction": "eu", "reason": "zero_coverage"},
                    {"domain": "fraud", "jurisdiction": "india", "reason": "thin_coverage"}
                ]
            }
        },
        "customer_packs": {
            "gap_plan": {
                "recommended_next_batch": [
                    {"domain": "aml", "jurisdiction": "canada", "reason": "zero_coverage"}
                ]
            }
        }
    }

    monkeypatch.setattr(module, "ROOT", tmp_path)

    gold_root = tmp_path / "evals" / "gold_cases"
    pack_root = tmp_path / "data" / "customer_evidence_packs"
    gold_root.mkdir(parents=True)
    pack_root.mkdir(parents=True)

    (gold_root / "aml_eu_case_001").mkdir()
    (pack_root / "aml_canada_pack_001").mkdir()

    plan = module.build_plan(
        status=status,
        batch_label="proof_batch_real_002",
        gold_limit=2,
        pack_limit=1,
        intake_root=tmp_path / "intake",
        gold_root=gold_root,
        pack_root=pack_root,
    )

    ids = [item["id"] for item in plan["items"]]
    source_dirs = [item["source_dir"] for item in plan["items"]]
    assert "aml_eu_case_002" in ids
    assert "fraud_india_case_001" in ids
    assert "aml_canada_pack_002" in ids
    assert "intake/proof_batch_real_002/aml_eu_case_002" in source_dirs
