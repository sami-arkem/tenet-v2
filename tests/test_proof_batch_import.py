from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_batch_import.py")
    spec = importlib.util.spec_from_file_location("proof_batch_import", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_batch_manifest_rejects_duplicate_ids(tmp_path: Path):
    module = load_module()
    manifest = tmp_path / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {"kind": "gold_case", "id": "aml_us_case_001", "source_dir": "intake/a"},
                    {"kind": "gold_case", "id": "aml_us_case_001", "source_dir": "intake/b"}
                ]
            }
        ),
        encoding="utf-8"
    )
    try:
        module.parse_batch_manifest(manifest)
    except ValueError as exc:
        assert "Duplicate item in batch" in str(exc)
    else:
        raise AssertionError("Expected duplicate batch ids to fail")


def test_parse_batch_manifest_normalizes_fields(tmp_path: Path):
    module = load_module()
    manifest = tmp_path / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "kind": "customer_pack",
                        "id": "AML-US-PACK-001",
                        "source_dir": "intake/packs/aml_us_pack_001",
                        "domains": ["AML", "Regulatory Reporting"],
                        "jurisdictions": ["US", "Australia"]
                    }
                ]
            }
        ),
        encoding="utf-8"
    )
    items = module.parse_batch_manifest(manifest)
    assert len(items) == 1
    assert items[0].item_id == "aml_us_pack_001"
    assert items[0].domains == ["aml", "regulatory_reporting"]
    assert items[0].jurisdictions == ["us", "australia"]


def test_assert_relative_path_rejects_parent_traversal():
    module = load_module()
    try:
        module.assert_relative_path("../bad")
    except ValueError as exc:
        assert "Parent traversal not allowed" in str(exc)
    else:
        raise AssertionError("Expected parent traversal to fail")


def test_get_target_dir_uses_correct_root():
    module = load_module()
    config = {
        "paths": {
            "gold_cases_root": "data/gold_cases",
            "customer_packs_root": "data/customer_evidence_packs"
        }
    }
    gold = module.get_target_dir(config, "gold_case", "aml_us_case_001")
    pack = module.get_target_dir(config, "customer_pack", "aml_us_pack_001")
    assert str(gold).endswith("data/gold_cases/aml_us_case_001")
    assert str(pack).endswith("data/customer_evidence_packs/aml_us_pack_001")
