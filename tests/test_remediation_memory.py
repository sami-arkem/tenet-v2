from pathlib import Path

from src.memory.audit_memory import build_audit_memory_snapshot
from src.memory.remediation_memory import (
    build_remediation_snapshot_from_audit_memory,
    compare_remediation_snapshots,
    write_remediation_snapshot,
    load_remediation_snapshot,
)


def _sample_output(audit_id: str, decision: str, findings: list[str], gaps: list[str]):
    return {
        "audit_meta": {"audit_id": audit_id},
        "entity_profile": {"legal_name": "Test Entity"},
        "audit_scope": {
            "audit_type": "aml_readiness_review",
            "jurisdictions": ["US"],
            "domains": ["aml", "governance"],
        },
        "deployment_decision": {
            "status": decision,
            "decision_rationale": "Deterministic rationale",
            "blocking_issues": [],
        },
        "findings": [{"control_id": x, "domain": "aml", "title": x} for x in findings],
        "missing_controls": [{"control_id": x, "title": x} for x in gaps],
        "missing_evidence": [{"control_id": x} for x in gaps],
        "remediation_roadmap": {
            "immediate_0_30_days": ["Action A"],
            "near_term_30_90_days": [],
            "medium_term_90_180_days": [],
            "strategic_180_plus_days": [],
        },
    }


def test_build_remediation_snapshot_from_audit_memory():
    audit_output = _sample_output("audit-1", "BLOCKED", ["AML-003", "GOV-001"], ["AML-003"])
    audit_memory = build_audit_memory_snapshot(audit_output)
    remediation = build_remediation_snapshot_from_audit_memory(audit_memory)

    assert remediation["audit_id"] == "audit-1"
    assert remediation["entity_name"] == "Test Entity"
    assert remediation["remediation_status_by_control"]["AML-003"]["status"] == "open"
    assert remediation["remediation_status_by_control"]["GOV-001"]["status"] == "in_progress"


def test_compare_remediation_snapshots_detects_closed_gap():
    prior_output = _sample_output("audit-1", "BLOCKED", ["AML-003", "GOV-001"], ["AML-003", "GOV-001"])
    current_output = _sample_output("audit-2", "CONDITIONALLY_APPROVED", ["GOV-001"], ["GOV-001"])

    prior = build_remediation_snapshot_from_audit_memory(build_audit_memory_snapshot(prior_output))
    current = build_remediation_snapshot_from_audit_memory(build_audit_memory_snapshot(current_output))
    comparison = compare_remediation_snapshots(prior, current)

    assert "AML-003" in comparison["newly_closed_controls"]
    assert "AML-003" in comparison["improved_controls"]
    assert "GOV-001" in comparison["still_open_controls"]


def test_write_and_load_remediation_snapshot(tmp_path: Path, monkeypatch):
    import src.memory.remediation_memory as remediation_memory

    monkeypatch.setattr(remediation_memory, "REMEDIATION_SNAPSHOT_ROOT", tmp_path / "remediation_snapshots")

    output = _sample_output("audit-1", "BLOCKED", ["AML-003"], ["AML-003"])
    audit_memory = build_audit_memory_snapshot(output)
    snapshot = build_remediation_snapshot_from_audit_memory(audit_memory)

    path = write_remediation_snapshot(snapshot)
    loaded = load_remediation_snapshot(path)

    assert loaded["audit_id"] == "audit-1"
    assert loaded["entity_name"] == "Test Entity"
    assert loaded["remediation_status_by_control"]["AML-003"]["status"] == "open"
