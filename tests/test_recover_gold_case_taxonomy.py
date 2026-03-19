from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/recover_gold_case_taxonomy.py")
    spec = importlib.util.spec_from_file_location("recover_gold_case_taxonomy", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_from_folder_name():
    module = load_module()
    case_dir = Path("evals/gold_cases/aml_australia_monitoring_escalation_gap")
    domains, jurisdictions = module.extract_from_folder_name(case_dir)
    assert any(candidate.value == "aml" for candidate in domains)
    assert any(candidate.value == "australia" for candidate in jurisdictions)


def test_choose_values_refuses_tie():
    module = load_module()
    candidates = [
        module.Candidate("aml", "folder_name", 80),
        module.Candidate("fraud", "folder_name", 80),
    ]
    chosen, reasons = module.choose_values(candidates, {"aml", "fraud"}, 70)
    assert chosen is None
    assert any("ambiguous top candidates" in reason for reason in reasons)


def test_recover_case_write_mode(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    case_dir = tmp_path / "evals" / "gold_cases" / "aml_eu_monitoring_gap"
    case_dir.mkdir(parents=True)
    (case_dir / "audit_context.json").write_text(
        json.dumps({
            "historical_context_is_non_authoritative": True,
            "deterministic_current_audit_truth_only": True,
        }),
        encoding="utf-8",
    )

    backup_root = tmp_path / "logs" / "bible_alignment" / "taxonomy_recovery_backups"
    result = module.recover_case(case_dir=case_dir, backup_root=backup_root, minimum_confidence=70, write=True)
    assert result.changed is True
    assert result.blocked is False
    payload = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    assert payload["domains"] == ["aml"]
    assert payload["jurisdictions"] == ["eu"]


def test_recover_case_blocks_when_no_confident_signal(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    case_dir = tmp_path / "evals" / "gold_cases" / "mystery_case"
    case_dir.mkdir(parents=True)
    (case_dir / "audit_context.json").write_text(json.dumps({}), encoding="utf-8")
    result = module.recover_case(case_dir=case_dir, backup_root=tmp_path / "logs" / "backups", minimum_confidence=70, write=False)
    assert result.blocked is True
    assert result.changed is False
