import json

from src.memory.audit_memory import build_audit_memory_snapshot
from src.memory.remediation_memory import (
    build_remediation_snapshot_from_audit_memory,
    compare_remediation_snapshots,
)

sample_prior_output = {
    "audit_meta": {"audit_id": "prior-audit"},
    "entity_profile": {"legal_name": "Demo Remediation Entity"},
    "audit_scope": {"audit_type": "aml_readiness_review", "jurisdictions": ["US"], "domains": ["aml", "governance"]},
    "deployment_decision": {"status": "BLOCKED", "decision_rationale": "Multiple control gaps"},
    "findings": [
        {"control_id": "AML-003", "domain": "aml", "title": "Transaction monitoring gap"},
        {"control_id": "GOV-001", "domain": "governance", "title": "Governance accountability gap"}
    ],
    "missing_controls": [
        {"control_id": "AML-003", "title": "Transaction Monitoring"},
        {"control_id": "GOV-001", "title": "Governance Roles and Escalation"}
    ],
    "missing_evidence": [{"control_id": "AML-003"}, {"control_id": "GOV-001"}],
    "remediation_roadmap": {
        "immediate_0_30_days": ["Stand up AML monitoring control design"],
        "near_term_30_90_days": [],
        "medium_term_90_180_days": [],
        "strategic_180_plus_days": []
    }
}

sample_current_output = {
    "audit_meta": {"audit_id": "current-audit"},
    "entity_profile": {"legal_name": "Demo Remediation Entity"},
    "audit_scope": {"audit_type": "aml_readiness_review", "jurisdictions": ["US"], "domains": ["aml", "governance"]},
    "deployment_decision": {"status": "CONDITIONALLY_APPROVED", "decision_rationale": "One gap remains"},
    "findings": [
        {"control_id": "GOV-001", "domain": "governance", "title": "Governance accountability gap"}
    ],
    "missing_controls": [
        {"control_id": "GOV-001", "title": "Governance Roles and Escalation"}
    ],
    "missing_evidence": [{"control_id": "GOV-001"}],
    "remediation_roadmap": {
        "immediate_0_30_days": ["Close governance escalation gap"],
        "near_term_30_90_days": [],
        "medium_term_90_180_days": [],
        "strategic_180_plus_days": []
    }
}

prior_memory = build_audit_memory_snapshot(sample_prior_output)
current_memory = build_audit_memory_snapshot(sample_current_output)

prior_remediation = build_remediation_snapshot_from_audit_memory(prior_memory)
current_remediation = build_remediation_snapshot_from_audit_memory(current_memory)

comparison = compare_remediation_snapshots(prior_remediation, current_remediation)
print(json.dumps(comparison, indent=2))
