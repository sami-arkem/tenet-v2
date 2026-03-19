from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/upgrade_legacy_gold_cases.py")
    spec = importlib.util.spec_from_file_location("upgrade_legacy_gold_cases", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_patch_audit_context_sets_required_flags():
    module = load_module()
    payload = {"domains": ["aml"], "jurisdictions": ["eu"]}
    out, reasons, blocked = module.patch_audit_context(payload)
    assert out["historical_context_is_non_authoritative"] is True
    assert out["deterministic_current_audit_truth_only"] is True
    assert blocked is False
    assert any(reason == "set historical_context_is_non_authoritative=true" for reason in reasons)


def test_patch_audit_context_blocks_missing_taxonomy():
    module = load_module()
    out, reasons, blocked = module.patch_audit_context({})
    assert blocked is True
    assert any("missing non-empty domains list" in reason for reason in reasons)
    assert any("missing non-empty jurisdictions list" in reason for reason in reasons)


def test_patch_expected_file_creates_rules_without_rewriting_expected_shape():
    module = load_module()
    payload = {
        "case_id": "aml_eu_case_001",
        "expected": {
            "equals": {"deployment_decision.status": "BLOCKED"},
            "contains": {},
            "minimums": {},
        },
    }
    out, reasons, blocked = module.patch_expected_file(payload, "expected_assertions.json")
    assert blocked is False
    assert out["rules"]["no_invented_pass_outcome"] is True
    assert "expected_assertions" not in out
    assert out["expected"]["equals"]["deployment_decision.status"] == "BLOCKED"
    assert any("created rules object" in reason for reason in reasons)


def test_patch_case_write_mode_creates_backup(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    case_dir = tmp_path / "evals" / "gold_cases" / "aml_eu_case_001"
    case_dir.mkdir(parents=True)
    (case_dir / "audit_context.json").write_text(json.dumps({
        "domains": ["aml"],
        "jurisdictions": ["eu"],
    }), encoding="utf-8")
    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "expected": {
            "equals": {"deployment_decision.status": "BLOCKED"},
            "contains": {},
            "minimums": {},
        }
    }), encoding="utf-8")

    backup_root = tmp_path / "logs" / "bible_alignment" / "legacy_gold_backups"
    result = module.patch_case(case_dir=case_dir, backup_root=backup_root, write=True)

    assert result.changed is True
    assert result.backup_dir is not None
    assert backup_root.exists()

    new_audit = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    new_expected = json.loads((case_dir / "expected_assertions.json").read_text(encoding="utf-8"))
    assert new_audit["historical_context_is_non_authoritative"] is True
    assert new_expected["rules"]["deterministic_current_truth_only"] is True
    assert isinstance(new_expected["expected"], dict)
