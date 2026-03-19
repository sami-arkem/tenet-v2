# fraud_us_monitoring_partial

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: fraud_readiness_review
- industry: fintech
- jurisdictions: US
- entity_name: Real Fraud US Monitoring Partial Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- BSA_AML
- GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, AML-003, GOV-001
- missing_evidence: AML-002, AML-003, GOV-001
- findings: AML-003, AML-002, GOV-001
- control_coverage_score minimum: 12

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
