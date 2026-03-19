from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/bible_alignment_gate.py")
    spec = importlib.util.spec_from_file_location("bible_alignment_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_summary_red():
    module = load_module()
    issues = [
        module.Issue("error", "deterministic_purity", "src/core/reason.py", "bad", 1),
        module.Issue("warning", "ui_style", "frontend/page.tsx", "warn", 2),
    ]
    summary = module.build_summary(issues)
    assert summary["status"] == "red"
    assert summary["severity_counts"]["error"] == 1
    assert summary["severity_counts"]["warning"] == 1


def test_validate_gold_case_dir(tmp_path: Path):
    module = load_module()
    config = {
        "required_bools_in_audit_context": [
            "historical_context_is_non_authoritative",
            "deterministic_current_audit_truth_only",
        ],
        "required_bools_in_expected_assertions_rules": [
            "no_invented_pass_outcome",
            "deterministic_current_truth_only",
            "historical_context_cannot_override_current_truth",
        ],
    }
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "audit_context.json").write_text(json.dumps({
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "historical_context_is_non_authoritative": True,
        "deterministic_current_audit_truth_only": True,
    }), encoding="utf-8")
    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "rules": {
            "no_invented_pass_outcome": True,
            "deterministic_current_truth_only": True,
            "historical_context_cannot_override_current_truth": True,
        },
        "expected": {
            "equals": {"deployment_decision.status": "BLOCKED"},
            "contains": {},
            "minimums": {},
        },
    }), encoding="utf-8")
    issues = module.validate_gold_case_dir(case_dir=case_dir, config=config)
    assert issues == []


def test_scan_for_markers(tmp_path: Path):
    module = load_module()
    root = tmp_path / "frontend"
    root.mkdir()
    file_path = root / "page.tsx"
    file_path.write_text("console.log('x')\nTODO remove\n", encoding="utf-8")
    issues = module.scan_for_markers(
        roots=[root],
        markers=["console.log(", "TODO"],
        category="ui_style",
        severity="error",
        max_hits_per_file=50,
        extensions=module.FRONTEND_EXTENSIONS,
    )
    assert len(issues) == 2


def test_check_report_surface(tmp_path: Path, monkeypatch):
    module = load_module()
    report_root = tmp_path / "src" / "export"
    report_root.mkdir(parents=True)
    (report_root / "bundle.py").write_text(
        "board_memo_markdown = 'x'\nclient_report_markdown = 'y'\npdf = True\ndocx = True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    issues = module.check_report_surface({"report_roots": ["src/export"]})
    assert issues == []


def test_render_markdown_includes_governing_bible():
    module = load_module()
    markdown = module.render_markdown(
        {
            "version": "v6",
            "governing_bible_version": "final bible final version",
            "governing_bible_path": "/tmp/final bible final version.md",
            "generated_at_epoch": 123,
            "summary": {
                "status": "green",
                "issue_count": 0,
                "severity_counts": {},
                "category_counts": {},
            },
            "issues": [],
        }
    )
    assert "governing_bible_version" in markdown
    assert "final bible final version" in markdown


def test_check_deterministic_purity_respects_model_boundary_allowlist(tmp_path: Path, monkeypatch):
    module = load_module()
    core_root = tmp_path / "core"
    core_root.mkdir()
    (core_root / "model_manager.py").write_text("from anthropic import Anthropic\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    issues = module.check_deterministic_purity(
        {
            "deterministic_roots": ["core"],
            "forbidden_in_deterministic_code": ["anthropic"],
            "model_boundary_allowlist": ["core/model_manager.py"],
        }
    )
    assert issues == []
