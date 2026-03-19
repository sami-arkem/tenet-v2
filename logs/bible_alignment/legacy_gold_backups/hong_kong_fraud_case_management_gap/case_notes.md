# hong_kong_fraud_case_management_gap

## Scenario
Real corpus-backed global expansion case.

## Audit context
- audit_type: fraud_readiness_review
- industry: payments
- jurisdictions: HONG_KONG
- entity_name: Real Hong Kong Fraud Case Management Gap
- domains: fraud, governance, remediation_tracking

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- HK_AML_BASELINE
- HK_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, AML-003, GOV-001, VEN-001
- missing_evidence: AML-002, AML-003, GOV-001, VEN-001
- findings: AML-003, AML-002, GOV-001, VEN-001
- control_coverage_score minimum: 9

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
