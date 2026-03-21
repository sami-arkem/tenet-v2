from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/gold_case_taxonomy_adjudication.py")
    spec = importlib.util.spec_from_file_location("gold_case_taxonomy_adjudication", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_targets_from_alignment(tmp_path: Path):
    module = load_module()
    path = tmp_path / "alignment.json"
    path.write_text(json.dumps({
        "issues": [
            {
                "category": "gold_case_contract",
                "path": "evals/gold_cases/aml_eu_case_001/audit_context.json",
                "message": "domains must be a non-empty list",
            },
            {
                "category": "gold_case_contract",
                "path": "evals/gold_cases/aml_eu_case_001/audit_context.json",
                "message": "jurisdictions must be a non-empty list",
            },
        ]
    }), encoding="utf-8")
    targets = module.extract_targets_from_alignment(path)
    assert len(targets) == 1
    assert targets[0].case_dir.name == "aml_eu_case_001"


def test_validate_decision():
    module = load_module()
    decision = module.validate_decision({
        "case_dir": "evals/gold_cases/aml_eu_case_001",
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "decided_by": "sami",
        "rationale": "Folder name and evidence indicate AML in EU scope",
        "evidence_refs": ["audit_context.json", "notes.md"],
    })
    assert decision.domains == ["aml"]
    assert decision.jurisdictions == ["eu"]


def test_apply_decisions_write_mode(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    case_dir = tmp_path / "evals" / "gold_cases" / "aml_eu_case_001"
    case_dir.mkdir(parents=True)
    (case_dir / "audit_context.json").write_text(json.dumps({}), encoding="utf-8")

    decisions_json = tmp_path / "decisions.json"
    decisions_json.write_text(json.dumps({
        "decisions": [
            {
                "case_dir": "evals/gold_cases/aml_eu_case_001",
                "domains": ["aml"],
                "jurisdictions": ["eu"],
                "decided_by": "sami",
                "rationale": "Folder name and evidence indicate AML in EU scope",
                "evidence_refs": ["audit_context.json"],
            }
        ]
    }), encoding="utf-8")

    report = module.apply_decisions(
        decisions_json=decisions_json,
        backup_root=tmp_path / "logs" / "backups",
        apply_report_json=tmp_path / "apply.json",
        apply_report_md=tmp_path / "apply.md",
        write=True,
    )
    payload = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    assert report["applied_count"] == 1
    assert payload["domains"] == ["aml"]
    assert payload["jurisdictions"] == ["eu"]
    assert payload["taxonomy_adjudication"]["decided_by"] == "sami"


def test_generate_dossiers(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    case_dir = tmp_path / "evals" / "gold_cases" / "aml_eu_case_001"
    case_dir.mkdir(parents=True)
    (case_dir / "audit_context.json").write_text(json.dumps({}), encoding="utf-8")
    (case_dir / "notes.md").write_text("AML controls for EU monitoring", encoding="utf-8")

    alignment = tmp_path / "alignment.json"
    alignment.write_text(json.dumps({
        "issues": [
            {
                "category": "gold_case_contract",
                "path": "evals/gold_cases/aml_eu_case_001/audit_context.json",
                "message": "domains must be a non-empty list",
            }
        ]
    }), encoding="utf-8")

    recovery = tmp_path / "recovery.json"
    recovery.write_text(json.dumps({"cases": []}), encoding="utf-8")

    summary = module.generate_dossiers(
        alignment_json=alignment,
        recovery_json=recovery,
        dossier_dir=tmp_path / "dossiers",
    )
    assert summary["dossier_count"] == 1
    assert (tmp_path / "dossiers" / "aml_eu_case_001.dossier.json").exists()
