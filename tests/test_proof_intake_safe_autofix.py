from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_intake_safe_autofix.py")
    spec = importlib.util.spec_from_file_location("proof_intake_safe_autofix", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_patch_audit_context_fills_safe_fields():
    module = load_module()
    payload = {"top_k": 5}
    out, reasons, blocked = module.patch_audit_context(
        payload=payload,
        expected_domains=["aml"],
        expected_jurisdictions=["eu"],
        placeholders_present=False,
    )
    assert out["historical_context_is_non_authoritative"] is True
    assert out["deterministic_current_audit_truth_only"] is True
    assert out["domains"] == ["aml"]
    assert out["jurisdictions"] == ["eu"]
    assert out["operator_fill_status"]["placeholder_free"] is True
    assert blocked is True
    assert any("entity_name still missing" in value for value in reasons)


def test_patch_expected_assertions_normalizes_schema_only():
    module = load_module()
    payload = {
        "expected_assertions": [
            {
                "type": "",
                "expected_value": "missing_control",
                "evidence_refs": ["notes.md"],
            }
        ]
    }
    out, _, blocked = module.patch_expected_assertions(payload)
    row = out["expected_assertions"][0]
    assert out["rules"]["no_invented_pass_outcome"] is True
    assert row["assertion_id"] == "assertion_001"
    assert row["type"] == "finding"
    assert row["control_id"] == ""
    assert row["regime_id"] == ""
    assert blocked is False


def test_patch_expected_assertions_does_not_invent_meaning():
    module = load_module()
    payload = {
        "expected": {
            "equals": {},
            "contains": {},
            "minimums": {},
        }
    }
    _, reasons, blocked = module.patch_expected_assertions(payload)
    assert blocked is True
    assert any("no meaningful values" in value for value in reasons)


def test_sync_workspace_entry_sets_provable_file_presence(tmp_path: Path):
    module = load_module()
    source_dir = tmp_path / "item"
    source_dir.mkdir()
    (source_dir / "audit_context.json").write_text("{}", encoding="utf-8")
    entry = {
        "required_files": ["audit_context.json"],
        "operator_repair": {
            "files_present": {"audit_context.json": False},
            "placeholders_removed": False,
        },
    }
    changed, reasons = module.sync_workspace_entry(entry, source_dir, placeholders_present=False)
    assert changed is True
    assert entry["operator_repair"]["files_present"]["audit_context.json"] is True
    assert entry["operator_repair"]["placeholders_removed"] is True
    assert any("synchronized files_present" in value for value in reasons)


def test_process_item_write_mode(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    source_dir = tmp_path / "intake" / "proof_batch_real_002" / "aml_eu_case_001"
    source_dir.mkdir(parents=True)

    (source_dir / "audit_context.json").write_text(
        json.dumps(
            {
                "entity_name": "AML EU case 001",
                "audit_type": "aml_readiness_review",
                "industry": "financial_services",
                "domains": ["aml"],
                "jurisdictions": ["eu"],
                "source_families": ["policy_docs"],
                "query_terms": ["aml escalation"],
                "top_k": 5,
                "operator_fill_status": {
                    "real_sources_attached": False,
                    "placeholder_free": False,
                    "ready_for_import": False,
                },
            }
        ),
        encoding="utf-8",
    )

    (source_dir / "expected_assertions.json").write_text(
        json.dumps(
            {
                "expected_assertions": [
                    {
                        "expected_value": "missing_alert_escalation_control",
                        "evidence_refs": ["notes.md"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    (source_dir / "case_notes.md").write_text("  Real notes about deterministic audit truth.  \n", encoding="utf-8")

    entry = {
        "id": "aml_eu_case_001",
        "kind": "gold_case",
        "source_dir": "intake/proof_batch_real_002/aml_eu_case_001",
        "domains": ["aml"],
        "jurisdictions": ["eu"],
        "required_files": ["audit_context.json", "expected_assertions.json", "case_notes.md"],
        "operator_repair": {
            "files_present": {
                "audit_context.json": False,
                "expected_assertions.json": False,
                "case_notes.md": False,
            },
            "placeholders_removed": False,
        },
    }

    result = module.process_item(entry=entry, backup_root=tmp_path / "backups", write=True)
    assert result.changed is True
    assert result.backup_dir is not None
    assert result.blocked is False

    audit_context = json.loads((source_dir / "audit_context.json").read_text(encoding="utf-8"))
    expected_assertions = json.loads((source_dir / "expected_assertions.json").read_text(encoding="utf-8"))
    case_notes = (source_dir / "case_notes.md").read_text(encoding="utf-8")

    assert audit_context["operator_fill_status"]["real_sources_attached"] is True
    assert audit_context["operator_fill_status"]["placeholder_free"] is True
    assert audit_context["operator_fill_status"]["ready_for_import"] is True
    assert expected_assertions["rules"]["deterministic_current_truth_only"] is True
    assert case_notes.endswith("\n")
    assert case_notes.strip() == "Real notes about deterministic audit truth."
    assert entry["operator_repair"]["files_present"]["audit_context.json"] is True
