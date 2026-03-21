# fraud_uk_case_management_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: fraud_readiness_review
- industry: payments
- jurisdictions: UK
- entity_name: Real Fraud UK Case Management Gap

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- UK_MLR
- GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, AML-003, GOV-001
- missing_evidence: AML-002, AML-003, GOV-001
- findings: AML-003, AML-002, GOV-001
- control_coverage_score minimum: 12

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
