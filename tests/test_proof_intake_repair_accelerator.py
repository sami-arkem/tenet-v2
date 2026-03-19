from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_intake_repair_accelerator.py")
    spec = importlib.util.spec_from_file_location("proof_intake_repair_accelerator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_workspace_entry_gold_case():
    module = load_module()
    entry = module.build_workspace_entry(
        plan_item={
            "kind": "gold_case",
            "id": "aml_eu_case_001",
            "title": "AML EU case 001",
            "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
            "domains": ["aml"],
            "jurisdictions": ["eu"],
            "reason": "zero_coverage",
        },
        readiness_item={
            "missing_required": ["expected_assertions.json"],
            "validation_errors": ["audit_context.json::missing_domains"],
            "placeholder_findings": ["case_notes.md::todo"],
            "ready": False,
        },
        blocker_item={
            "blocker_count": 3,
            "blocker_score": 240,
            "primary_blocker_type": "missing_required",
            "issues": [{"issue_type": "missing_required", "message": "missing expected_assertions", "fix_hint": "add file"}],
        },
    )
    assert entry["required_files"] == ["audit_context.json", "expected_assertions.json", "case_notes.md"]
    assert entry["status"] == "blocked"
    assert entry["operator_repair"]["completed"] is False


def test_validate_operator_repair_decided_ok():
    module = load_module()
    entry = {
        "id": "aml_eu_case_001",
        "kind": "gold_case",
        "status": "blocked",
        "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
        "operator_repair": {
            "completed": True,
            "files_present": {
                "audit_context.json": True,
                "expected_assertions.json": True,
                "case_notes.md": True,
            },
            "audit_context_checked": True,
            "expected_assertions_checked": True,
            "case_notes_checked": True,
            "placeholders_removed": True,
            "repair_notes": "Filled real deterministic expected assertions and removed placeholder text.",
            "evidence_refs": ["intake/proof_batch_real_002/aml_eu_case_001/audit_context.json"],
        },
    }
    issues = module.validate_operator_repair(entry)
    assert issues == []


def test_validate_operator_repair_blocks_missing_refs():
    module = load_module()
    entry = {
        "id": "aml_eu_case_001",
        "kind": "gold_case",
        "status": "blocked",
        "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
        "operator_repair": {
            "completed": True,
            "files_present": {
                "audit_context.json": True,
                "expected_assertions.json": True,
                "case_notes.md": True,
            },
            "audit_context_checked": True,
            "expected_assertions_checked": True,
            "case_notes_checked": True,
            "placeholders_removed": True,
            "repair_notes": "Filled content.",
            "evidence_refs": [],
        },
    }
    issues = module.validate_operator_repair(entry)
    codes = {issue.code for issue in issues}
    assert "repair.invalid_evidence_refs" in codes


def test_compile_ready_manifest():
    module = load_module()
    workspace = {
        "entries": [
            {
                "kind": "gold_case",
                "id": "aml_eu_case_001",
                "title": "AML EU case 001",
                "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
                "domains": ["aml"],
                "jurisdictions": ["eu"],
                "operator_repair": {"completed": True},
            },
            {
                "kind": "customer_pack",
                "id": "aml_us_pack_001",
                "title": "AML US pack 001",
                "source_dir": "intake/proof_batch_real_002/aml_us_pack_001",
                "domains": ["aml"],
                "jurisdictions": ["us"],
                "operator_repair": {"completed": False},
            },
        ]
    }
    manifest = module.compile_ready_manifest(workspace)
    assert len(manifest["items"]) == 1
    assert manifest["items"][0]["id"] == "aml_eu_case_001"


def test_validate_workspace_duplicate_ids():
    module = load_module()
    workspace = {
        "entries": [
            {
                "id": "aml_eu_case_001",
                "kind": "gold_case",
                "status": "blocked",
                "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
                "operator_repair": {
                    "completed": False,
                    "files_present": {"audit_context.json": False, "expected_assertions.json": False, "case_notes.md": False},
                    "audit_context_checked": False,
                    "expected_assertions_checked": False,
                    "case_notes_checked": False,
                    "placeholders_removed": False,
                    "repair_notes": "",
                    "evidence_refs": [],
                },
            },
            {
                "id": "aml_eu_case_001",
                "kind": "gold_case",
                "status": "blocked",
                "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
                "operator_repair": {
                    "completed": False,
                    "files_present": {"audit_context.json": False, "expected_assertions.json": False, "case_notes.md": False},
                    "audit_context_checked": False,
                    "expected_assertions_checked": False,
                    "case_notes_checked": False,
                    "placeholders_removed": False,
                    "repair_notes": "",
                    "evidence_refs": [],
                },
            },
        ]
    }
    report = module.validate_workspace(workspace)
    assert any(issue["code"] == "workspace.duplicate_id" for issue in report["issues"])
