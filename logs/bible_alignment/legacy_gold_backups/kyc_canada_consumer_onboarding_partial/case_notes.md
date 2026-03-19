# kyc_canada_consumer_onboarding_partial

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: kyc_kyb_policy_and_control_review
- industry: fintech
- jurisdictions: CANADA
- entity_name: Real Canada Consumer Onboarding Partial
- domains: kyc_kyb, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- CA_AML_BASELINE
- CA_SANCTIONS_BASELINE
- CA_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, GOV-001, KYB-001, KYC-001
- missing_evidence: AML-002, GOV-001, KYB-001, KYC-001
- findings: KYB-001, KYC-001, AML-002, GOV-001
- control_coverage_score minimum: 0

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
