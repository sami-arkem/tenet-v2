from pathlib import Path

from src.memory.historical_context import (
    build_historical_context,
    build_historical_query_terms,
    load_trend_summary_for_entity,
)


def test_load_trend_summary_for_unknown_entity_returns_none():
    assert load_trend_summary_for_entity("Definitely Missing Entity") is None


def test_build_historical_context_without_history():
    ctx = build_historical_context("Definitely Missing Entity")
    assert ctx["has_history"] is False
    assert ctx["prior_recurring_missing_controls"] == []
    assert ctx["prior_recurring_findings"] == []


def test_build_historical_context_with_real_history():
    # uses trend files already backfilled in the repo
    path = Path("data/memory/trends")
    existing = sorted(path.glob("*.json"))
    assert existing, "Expected at least one trend file"

    entity_slug = existing[0].stem
    entity_name = entity_slug.replace("_", " ")
    ctx = build_historical_context(entity_name)
    assert "has_history" in ctx
    assert ctx["entity_name"]
    if ctx["audit_count"] < 2:
        assert ctx["has_history"] is False


def test_build_historical_query_terms():
    terms = build_historical_query_terms(
        {
            "has_history": True,
            "prior_recurring_missing_controls": ["GOV-001", "SAN-001"],
            "prior_recurring_findings": ["AML-003"],
            "prior_decision_trajectory": {"status": "improving", "latest_decision": "CONDITIONALLY_APPROVED"},
            "prior_remediation_trajectory": {"status": "stable"},
            "repeated_governance_weaknesses": ["GOV-001"],
            "repeated_screening_weaknesses": ["SAN-001"],
            "repeated_licensing_weaknesses": [],
            "repeated_remediation_weaknesses": [],
        }
    )
    assert "historical missing control GOV-001" in terms
    assert "historical finding AML-003" in terms
    assert "historical decision trajectory improving" in terms
