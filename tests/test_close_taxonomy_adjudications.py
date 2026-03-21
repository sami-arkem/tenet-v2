from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/close_taxonomy_adjudications.py")
    spec = importlib.util.spec_from_file_location("close_taxonomy_adjudications", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_read_dossier_index(tmp_path: Path):
    module = load_module()
    path = tmp_path / "dossier_index.json"
    path.write_text(json.dumps({
        "dossiers": [
            {"case_dir": "evals/gold_cases/aml_eu_case_001"},
            {"case_dir": "evals/gold_cases/fraud_us_case_001"},
        ]
    }), encoding="utf-8")
    rows = module.read_dossier_index(path)
    assert rows == [
        "evals/gold_cases/aml_eu_case_001",
        "evals/gold_cases/fraud_us_case_001",
    ]


def test_validate_decisions_against_dossiers_ok():
    module = load_module()
    dossiers = ["evals/gold_cases/aml_eu_case_001"]
    rows = [
        {
            "case_dir": "evals/gold_cases/aml_eu_case_001",
            "domains": ["aml"],
            "jurisdictions": ["eu"],
            "decided_by": "sami",
            "rationale": "Clear evidence from dossier",
            "evidence_refs": ["audit_context.json", "notes.md"],
        }
    ]
    issues, normalized, missing = module.validate_decisions_against_dossiers(
        dossier_case_dirs=dossiers,
        decision_rows=rows,
    )
    assert issues == []
    assert missing == []
    assert normalized[0]["domains"] == ["aml"]
    assert normalized[0]["jurisdictions"] == ["eu"]


def test_validate_decisions_against_dossiers_missing_and_duplicate():
    module = load_module()
    dossiers = [
        "evals/gold_cases/aml_eu_case_001",
        "evals/gold_cases/fraud_us_case_001",
    ]
    rows = [
        {
            "case_dir": "evals/gold_cases/aml_eu_case_001",
            "domains": ["aml"],
            "jurisdictions": ["eu"],
            "decided_by": "sami",
            "rationale": "Clear evidence from dossier",
            "evidence_refs": ["audit_context.json"],
        },
        {
            "case_dir": "evals/gold_cases/aml_eu_case_001",
            "domains": ["aml"],
            "jurisdictions": ["eu"],
            "decided_by": "sami",
            "rationale": "duplicate",
            "evidence_refs": ["audit_context.json"],
        },
    ]
    issues, normalized, missing = module.validate_decisions_against_dossiers(
        dossier_case_dirs=dossiers,
        decision_rows=rows,
    )
    codes = {issue.code for issue in issues}
    assert "decision.duplicate_case_dir" in codes
    assert "decision.missing_for_target_case" in codes
    assert missing == ["evals/gold_cases/fraud_us_case_001"]


def test_build_adjudication_queue(tmp_path: Path):
    module = load_module()
    out = module.build_adjudication_queue(
        dossier_case_dirs=["evals/gold_cases/aml_eu_case_001"],
        decisions_rows=[],
        output_dir=tmp_path,
    )
    assert out["target_case_count"] == 1
    assert (tmp_path / "adjudication_queue.json").exists()
    assert (tmp_path / "adjudication_queue.md").exists()
