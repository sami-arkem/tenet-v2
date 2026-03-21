from pathlib import Path

from src.memory.trend_intelligence import (
    build_entity_trend_summary,
    write_entity_trend_summary,
)


def _audit_snapshot(audit_id: str, written_at: str, decision: str, domains: list[str], findings: list[str], gaps: list[str]):
    return {
        "written_at_utc": written_at,
        "audit_id": audit_id,
        "entity_name": "Trend Test Entity",
        "jurisdictions": ["US"],
        "domains": domains,
        "deployment_decision": {"status": decision},
        "findings_control_ids": findings,
        "missing_controls_control_ids": gaps,
    }


def test_build_entity_trend_summary_detects_recurring_controls_and_trajectory():
    audit_snapshots = [
        _audit_snapshot("audit-1", "2026-01-01T00:00:00+00:00", "BLOCKED", ["governance", "sanctions"], ["GOV-001", "SAN-001"], ["GOV-001", "SAN-001"]),
        _audit_snapshot("audit-2", "2026-02-01T00:00:00+00:00", "CONDITIONALLY_APPROVED", ["governance", "transaction_screening"], ["GOV-001"], ["GOV-001"]),
        _audit_snapshot("audit-3", "2026-03-01T00:00:00+00:00", "APPROVED", ["governance"], [], []),
    ]
    remediation_comparisons = [
        {
            "newly_closed_controls": ["SAN-001"],
            "newly_open_controls": [],
            "still_open_controls": ["GOV-001"],
            "improved_controls": ["SAN-001"],
        },
        {
            "newly_closed_controls": ["GOV-001"],
            "newly_open_controls": [],
            "still_open_controls": [],
            "improved_controls": ["GOV-001"],
        },
    ]

    summary = build_entity_trend_summary(audit_snapshots, remediation_comparisons)

    assert summary["audit_count"] == 3
    assert summary["decision_trajectory"]["status"] == "improving"
    assert summary["recurring_missing_controls"][0]["control_id"] == "GOV-001"
    assert summary["repeated_governance_weaknesses"][0]["control_id"] == "GOV-001"
    assert summary["repeated_screening_weaknesses"] == []
    assert summary["remediation_improvement_trajectory"]["status"] == "improving"


def test_build_entity_trend_summary_handles_insufficient_history():
    audit_snapshots = [
        _audit_snapshot("audit-1", "2026-01-01T00:00:00+00:00", "BLOCKED", ["governance"], ["GOV-001"], ["GOV-001"]),
    ]
    summary = build_entity_trend_summary(audit_snapshots, [])
    assert summary["decision_trajectory"]["status"] == "insufficient_history"
    assert summary["remediation_improvement_trajectory"]["status"] == "insufficient_history"


def test_write_entity_trend_summary(tmp_path: Path, monkeypatch):
    import src.memory.trend_intelligence as trend_intelligence

    audit_root = tmp_path / "snapshots"
    trend_root = tmp_path / "trends"
    remediation_root = tmp_path / "remediation_comparisons"

    entity_dir = audit_root / "trend_test_entity"
    entity_dir.mkdir(parents=True, exist_ok=True)

    (entity_dir / "audit-1.json").write_text(
        """{
          \"written_at_utc\": \"2026-01-01T00:00:00+00:00\",
          \"audit_id\": \"audit-1\",
          \"entity_name\": \"Trend Test Entity\",
          \"jurisdictions\": [\"US\"],
          \"domains\": [\"governance\"],
          \"deployment_decision\": {\"status\": \"BLOCKED\"},
          \"findings_control_ids\": [\"GOV-001\"],
          \"missing_controls_control_ids\": [\"GOV-001\"]
        }""",
        encoding="utf-8",
    )

    monkeypatch.setattr(trend_intelligence, "AUDIT_MEMORY_ROOT", audit_root)
    monkeypatch.setattr(trend_intelligence, "TREND_ROOT", trend_root)
    monkeypatch.setattr(trend_intelligence, "REMEDIATION_COMPARISON_ROOT", remediation_root)

    out = write_entity_trend_summary("trend test entity")
    assert out is not None
    assert out.exists()
