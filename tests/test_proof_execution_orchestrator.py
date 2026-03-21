from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/proof_execution_orchestrator.py")
    spec = importlib.util.spec_from_file_location("proof_execution_orchestrator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_shard_ready_items():
    module = load_module()
    items = [
        module.ReadinessItem(
            kind="gold_case",
            item_id=f"aml_us_case_00{i}",
            title="x",
            source_dir="intake/x",
            domains=["aml"],
            jurisdictions=["us"],
            reason="coverage_gap",
            ready=True,
            readiness_score=1.0,
            missing_required=[],
            validation_errors=[],
            placeholder_findings=[],
        )
        for i in range(1, 8)
    ]
    shards = module.shard_ready_items(items, 3)
    assert [len(s) for s in shards] == [3, 3, 1]


def test_write_batch_manifests(tmp_path: Path):
    module = load_module()
    items = [[
        module.ReadinessItem(
            kind="gold_case",
            item_id="aml_us_case_001",
            title="AML US case 001",
            source_dir="intake/aml_us_case_001",
            domains=["aml"],
            jurisdictions=["us"],
            reason="coverage_gap",
            ready=True,
            readiness_score=1.0,
            missing_required=[],
            validation_errors=[],
            placeholder_findings=[],
        )
    ]]
    out = module.write_batch_manifests(
        batch_label="proof_batch_real_002",
        shards=items,
        output_dir=tmp_path,
    )
    assert len(out) == 1
    manifest = json.loads((tmp_path / "proof_batch_real_002_shard_001.json").read_text())
    assert manifest["items"][0]["id"] == "aml_us_case_001"


def test_write_operator_tasks(tmp_path: Path):
    module = load_module()
    planned = [
        module.PlannedItem(
            kind="gold_case",
            item_id="aml_us_case_001",
            title="AML US case 001",
            source_dir="intake/aml_us_case_001",
            domains=["aml"],
            jurisdictions=["us"],
            reason="zero_coverage",
        )
    ]
    readiness = [
        module.ReadinessItem(
            kind="gold_case",
            item_id="aml_us_case_001",
            title="AML US case 001",
            source_dir="intake/aml_us_case_001",
            domains=["aml"],
            jurisdictions=["us"],
            reason="zero_coverage",
            ready=False,
            readiness_score=0.6,
            missing_required=["expected_assertions.json"],
            validation_errors=["audit_context.json::missing_domains"],
            placeholder_findings=[],
        )
    ]
    summary = module.write_operator_tasks(
        batch_label="proof_batch_real_002",
        planned_items=planned,
        readiness_items=readiness,
        output_dir=tmp_path,
    )
    assert summary["blocked_count"] == 1
    task_file = tmp_path / "operator_tasks" / "aml_us_case_001.md"
    assert task_file.exists()
    body = task_file.read_text()
    assert "expected_assertions.json" in body
    assert "missing_domains" in body


def test_parse_plan_and_readiness(tmp_path: Path):
    module = load_module()
    plan = tmp_path / "plan.json"
    readiness = tmp_path / "readiness.json"

    plan.write_text(json.dumps({
        "batch_label": "proof_batch_real_002",
        "items": [{
            "kind": "gold_case",
            "id": "aml_us_case_001",
            "title": "AML US case 001",
            "source_dir": "intake/aml_us_case_001",
            "domains": ["aml"],
            "jurisdictions": ["us"],
            "reason": "zero_coverage"
        }]
    }), encoding="utf-8")

    readiness.write_text(json.dumps({
        "batch_label": "proof_batch_real_002",
        "items": [{
            "kind": "gold_case",
            "id": "aml_us_case_001",
            "title": "AML US case 001",
            "source_dir": "intake/aml_us_case_001",
            "domains": ["aml"],
            "jurisdictions": ["us"],
            "reason": "zero_coverage",
            "ready": True,
            "readiness_score": 1.0,
            "missing_required": [],
            "validation_errors": [],
            "placeholder_findings": []
        }]
    }), encoding="utf-8")

    batch_label, planned = module.parse_plan(plan)
    readiness_label, ready_items = module.parse_readiness(readiness)

    assert batch_label == "proof_batch_real_002"
    assert readiness_label == "proof_batch_real_002"
    assert planned[0].item_id == "aml_us_case_001"
    assert ready_items[0].ready is True
