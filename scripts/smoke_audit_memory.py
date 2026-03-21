import json
from pathlib import Path

from src.memory.audit_memory import (
    build_audit_memory_snapshot,
    compare_audit_memory_snapshots,
)

sample_a = {
    "audit_meta": {"audit_id": "audit-a"},
    "entity_profile": {"legal_name": "Demo Entity"},
    "audit_scope": {"audit_type": "aml_readiness_review", "jurisdictions": ["US"], "domains": ["aml", "governance"]},
    "deployment_decision": {"status": "BLOCKED", "decision_rationale": "Initial gaps"},
    "findings": [{"control_id": "AML-003"}, {"control_id": "GOV-001"}],
    "missing_controls": [{"control_id": "AML-003"}, {"control_id": "GOV-001"}],
    "missing_evidence": [{"control_id": "AML-003"}],
    "remediation_roadmap": {"immediate_0_30_days": ["Implement AML-003"]},
}
sample_b = {
    "audit_meta": {"audit_id": "audit-b"},
    "entity_profile": {"legal_name": "Demo Entity"},
    "audit_scope": {"audit_type": "aml_readiness_review", "jurisdictions": ["US"], "domains": ["aml", "governance"]},
    "deployment_decision": {"status": "CONDITIONALLY_APPROVED", "decision_rationale": "Some gaps closed"},
    "findings": [{"control_id": "GOV-001"}],
    "missing_controls": [{"control_id": "GOV-001"}],
    "missing_evidence": [{"control_id": "GOV-001"}],
    "remediation_roadmap": {"immediate_0_30_days": ["Close GOV-001"]},
}

prior = build_audit_memory_snapshot(sample_a)
current = build_audit_memory_snapshot(sample_b)
comparison = compare_audit_memory_snapshots(prior, current)
print(json.dumps(comparison, indent=2))
