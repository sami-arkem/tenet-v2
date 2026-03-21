# sanctions_uae_wallet_screening_partial

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: sanctions_readiness_review
- industry: crypto
- jurisdictions: UAE
- entity_name: Real UAE Wallet Screening Partial
- domains: sanctions, transaction_screening, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- UAE_AML_BASELINE
- UAE_SANCTIONS_BASELINE
- UAE_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: GOV-001, SAN-001, AML-003
- missing_evidence: GOV-001, SAN-001, AML-003
- findings: AML-003, SAN-001, GOV-001
- control_coverage_score minimum: 23

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
