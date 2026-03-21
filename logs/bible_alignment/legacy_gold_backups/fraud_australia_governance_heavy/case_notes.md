# fraud_australia_governance_heavy

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: fraud_readiness_review
- industry: fintech
- jurisdictions: AUSTRALIA
- entity_name: Real Australia Fraud Governance Heavy

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- AU_AML_BASELINE
- AU_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, AML-003, GOV-001, VEN-001
- missing_evidence: AML-002, AML-003, GOV-001, VEN-001
- findings: AML-003, AML-002, GOV-001, VEN-001
- control_coverage_score minimum: 9

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
