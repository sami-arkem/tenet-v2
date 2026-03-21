# kyc_us_consumer_onboarding_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: kyc_kyb_policy_and_control_review
- industry: fintech
- jurisdictions: US
- entity_name: Real KYC US Consumer Gap Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- CIP_KYC
- CDD_BO

## Expected control position
- missing_controls: AML-002, GOV-001, KYB-001, KYC-001
- missing_evidence: AML-002, GOV-001, KYB-001, KYC-001
- findings: KYB-001, KYC-001, AML-002, GOV-001
- control_coverage_score minimum: 0

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
