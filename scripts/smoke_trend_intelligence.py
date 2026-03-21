import json

from src.memory.trend_intelligence import build_entity_trend_summary

audit_snapshots = [
    {
        "written_at_utc": "2026-01-01T00:00:00+00:00",
        "audit_id": "audit-1",
        "entity_name": "Demo Trend Entity",
        "jurisdictions": ["US"],
        "domains": ["governance", "sanctions"],
        "deployment_decision": {"status": "BLOCKED"},
        "findings_control_ids": ["GOV-001", "SAN-001"],
        "missing_controls_control_ids": ["GOV-001", "SAN-001"],
    },
    {
        "written_at_utc": "2026-02-01T00:00:00+00:00",
        "audit_id": "audit-2",
        "entity_name": "Demo Trend Entity",
        "jurisdictions": ["US"],
        "domains": ["governance", "transaction_screening"],
        "deployment_decision": {"status": "CONDITIONALLY_APPROVED"},
        "findings_control_ids": ["GOV-001"],
        "missing_controls_control_ids": ["GOV-001"],
    },
    {
        "written_at_utc": "2026-03-01T00:00:00+00:00",
        "audit_id": "audit-3",
        "entity_name": "Demo Trend Entity",
        "jurisdictions": ["US"],
        "domains": ["governance"],
        "deployment_decision": {"status": "APPROVED"},
        "findings_control_ids": [],
        "missing_controls_control_ids": [],
    },
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
print(json.dumps(summary, indent=2))
