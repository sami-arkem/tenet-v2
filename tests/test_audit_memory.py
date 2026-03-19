from pathlib import Path

from src.memory.audit_memory import (
    build_audit_memory_snapshot,
    compare_audit_memory_snapshots,
    write_audit_memory_snapshot,
    load_audit_memory_snapshot,
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
            "decision_rationale": "Deterministic test rationale",
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


def test_build_audit_memory_snapshot():
    out = _sample_output("audit-1", "BLOCKED", ["AML-003"], ["AML-003"])
    snap = build_audit_memory_snapshot(out)
    assert snap["audit_id"] == "audit-1"
    assert snap["entity_name"] == "Test Entity"
    assert snap["deployment_decision"]["status"] == "BLOCKED"
    assert "AML-003" in snap["findings_control_ids"]
    assert "AML-003" in snap["missing_controls_control_ids"]


def test_compare_audit_memory_snapshots():
    prior = build_audit_memory_snapshot(_sample_output("audit-1", "BLOCKED", ["AML-003", "GOV-001"], ["AML-003", "GOV-001"]))
    current = build_audit_memory_snapshot(_sample_output("audit-2", "CONDITIONALLY_APPROVED", ["GOV-001"], ["GOV-001"]))
    comparison = compare_audit_memory_snapshots(prior, current)
    assert comparison["prior_decision"] == "BLOCKED"
    assert comparison["current_decision"] == "CONDITIONALLY_APPROVED"
    assert "AML-003" in comparison["closed_gaps"]
    assert "AML-003" in comparison["closed_findings"]
    assert "GOV-001" in comparison["unchanged_gaps"]


def test_write_and_load_snapshot(tmp_path: Path, monkeypatch):
    import src.memory.audit_memory as audit_memory

    monkeypatch.setattr(audit_memory, "MEMORY_ROOT", tmp_path / "snapshots")
    out = _sample_output("audit-1", "BLOCKED", ["AML-003"], ["AML-003"])
    path = write_audit_memory_snapshot(out)
    loaded = load_audit_memory_snapshot(path)
    assert loaded["audit_id"] == "audit-1"
    assert loaded["entity_name"] == "Test Entity"
