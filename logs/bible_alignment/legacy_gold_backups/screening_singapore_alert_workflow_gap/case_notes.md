# screening_singapore_alert_workflow_gap

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: transaction_screening_review
- industry: payments
- jurisdictions: SINGAPORE
- entity_name: Real Singapore Screening Alert Workflow Gap
- domains: transaction_screening, sanctions, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- SG_SANCTIONS_BASELINE

## Expected control position
- missing_controls: AML-003, GOV-001, SAN-001
- missing_evidence: AML-003, GOV-001, SAN-001
- findings: AML-003, SAN-001, GOV-001
- control_coverage_score minimum: 23

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
