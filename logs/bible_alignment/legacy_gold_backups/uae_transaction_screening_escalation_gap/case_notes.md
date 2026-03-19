# uae_transaction_screening_escalation_gap

## Scenario
Real corpus-backed global expansion case.

## Audit context
- audit_type: transaction_screening_review
- industry: payments
- jurisdictions: UAE
- entity_name: Real UAE Transaction Screening Escalation Gap
- domains: transaction_screening, sanctions, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- UAE_SANCTIONS_BASELINE

## Expected control position
- missing_controls: AML-003, GOV-001, SAN-001
- missing_evidence: AML-003, GOV-001, SAN-001
- findings: AML-003, SAN-001, GOV-001
- control_coverage_score minimum: 23

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
