# fraud_uae_case_management_partial

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: fraud_readiness_review
- industry: fintech
- jurisdictions: UAE
- entity_name: Real UAE Fraud Case Management Partial
- domains: fraud, governance, remediation_tracking

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- UAE_AML_BASELINE
- UAE_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, AML-003, GOV-001, VEN-001
- missing_evidence: AML-002, AML-003, GOV-001, VEN-001
- findings: AML-003, AML-002, GOV-001, VEN-001
- control_coverage_score minimum: 9

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
