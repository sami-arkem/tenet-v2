from __future__ import annotations

import json
from pathlib import Path

from core.proof_program import ProofProgramRegistry


def test_readiness_is_blocked_when_targets_not_met(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    registry.set_targets(gold_target=3, customer_pack_target=2)
    registry.upsert_gold_case(
        case_id="GC-001",
        title="UK AML source-of-funds pass",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        control_id="AML-UK-001",
        status="PASS",
        now_epoch=100,
    )
    registry.upsert_customer_pack(
        pack_id="CP-001",
        customer_name="Acme Ltd",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        status="STABLE",
        now_epoch=101,
    )
    registry.set_final_execution(suite_green=True, ref="abc123", now_epoch=102)

    summary = registry.summarize()

    assert summary.overall_ready is False
    assert summary.gold_target_gap == 2
    assert summary.customer_pack_target_gap == 1
    assert "gold case target gap: 2" in summary.blockers
    assert "customer pack target gap: 1" in summary.blockers


def test_readiness_is_blocked_when_gold_cases_fail(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    registry.set_targets(gold_target=1, customer_pack_target=1)
    registry.upsert_gold_case(
        case_id="GC-FAIL",
        title="Failing case",
        domain="Sanctions",
        jurisdiction="US",
        framework="OFAC",
        control_id="SAN-001",
        status="FAIL",
        now_epoch=100,
    )
    registry.upsert_customer_pack(
        pack_id="CP-OK",
        customer_name="Northwind",
        domain="Sanctions",
        jurisdiction="US",
        framework="OFAC",
        status="STABLE",
        now_epoch=100,
    )
    registry.set_final_execution(suite_green=True, ref="run-1", now_epoch=100)

    summary = registry.summarize()

    assert summary.overall_ready is False
    assert summary.gold_failing == 1
    assert "1 gold case(s) failing" in summary.blockers


def test_readiness_is_blocked_when_final_execution_is_red(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    registry.set_targets(gold_target=1, customer_pack_target=1)
    registry.upsert_gold_case(
        case_id="GC-001",
        title="Passing case",
        domain="KYC",
        jurisdiction="EU",
        framework="AMLD",
        control_id="KYC-001",
        status="PASS",
        now_epoch=100,
    )
    registry.upsert_customer_pack(
        pack_id="CP-001",
        customer_name="Contoso",
        domain="KYC",
        jurisdiction="EU",
        framework="AMLD",
        status="STABLE",
        now_epoch=100,
    )
    registry.set_final_execution(
        suite_green=False,
        failing_gate_names=["export_gate", "release_gate"],
        ref="run-2",
        now_epoch=100,
    )

    summary = registry.summarize()

    assert summary.overall_ready is False
    assert summary.final_execution_green is False
    assert summary.failing_gates == ["export_gate", "release_gate"]
    assert "final execution discipline not green: export_gate, release_gate" in summary.blockers


def test_readiness_turns_green_only_when_all_targets_and_gates_are_green(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    registry.set_targets(gold_target=2, customer_pack_target=2)
    registry.upsert_gold_case(
        case_id="GC-001",
        title="UK AML pass",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        control_id="AML-001",
        status="PASS",
        now_epoch=100,
    )
    registry.upsert_gold_case(
        case_id="GC-002",
        title="US sanctions pass",
        domain="Sanctions",
        jurisdiction="US",
        framework="OFAC",
        control_id="SAN-001",
        status="PASS",
        now_epoch=101,
    )
    registry.upsert_customer_pack(
        pack_id="CP-001",
        customer_name="Acme",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        status="STABLE",
        now_epoch=100,
    )
    registry.upsert_customer_pack(
        pack_id="CP-002",
        customer_name="Globex",
        domain="Sanctions",
        jurisdiction="US",
        framework="OFAC",
        status="ACTIVE",
        now_epoch=101,
    )
    registry.set_final_execution(suite_green=True, ref="run-3", now_epoch=102)

    summary = registry.summarize()

    assert summary.overall_ready is True
    assert summary.blockers == []
    assert summary.coverage["domains"] == {"AML": 1, "Sanctions": 1}
    assert summary.coverage["jurisdictions"] == {"UK": 1, "US": 1}
    assert summary.coverage["frameworks"] == {"FCA": 1, "OFAC": 1}


def test_outputs_are_written_as_json_and_markdown(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    registry.set_targets(gold_target=1, customer_pack_target=1)
    registry.upsert_gold_case(
        case_id="GC-001",
        title="Case",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        control_id="AML-001",
        status="PASS",
        now_epoch=100,
    )
    registry.upsert_customer_pack(
        pack_id="CP-001",
        customer_name="Acme",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        status="STABLE",
        now_epoch=100,
    )
    registry.set_final_execution(suite_green=True, ref="run-4", now_epoch=100)

    json_path = tmp_path / "readiness_summary.json"
    markdown_path = tmp_path / "readiness_summary.md"

    summary = registry.write_readiness_outputs(json_path=json_path, markdown_path=markdown_path)

    assert summary.overall_ready is True
    assert json.loads(json_path.read_text(encoding="utf-8"))["overall_ready"] is True
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Tenet Proof Program Readiness" in markdown
    assert "- overall_ready: YES" in markdown


def test_upsert_preserves_created_timestamp_and_updates_updated_timestamp(tmp_path: Path) -> None:
    registry = ProofProgramRegistry(tmp_path / "manifest.json")
    first = registry.upsert_gold_case(
        case_id="GC-001",
        title="Original",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        control_id="AML-001",
        status="PASS",
        now_epoch=100,
    )
    second = registry.upsert_gold_case(
        case_id="GC-001",
        title="Revised",
        domain="AML",
        jurisdiction="UK",
        framework="FCA",
        control_id="AML-001",
        status="PASS",
        now_epoch=200,
    )

    assert first.created_at_epoch == 100
    assert second.created_at_epoch == 100
    assert second.updated_at_epoch == 200
