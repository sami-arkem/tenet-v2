# kyb_singapore_beneficial_ownership_gap

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: kyc_kyb_policy_and_control_review
- industry: fintech
- jurisdictions: SINGAPORE
- entity_name: Real Singapore KYB Beneficial Ownership Gap
- domains: kyc_kyb, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- SG_AML_BASELINE
- SG_SANCTIONS_BASELINE
- SG_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-002, GOV-001, KYB-001, KYC-001
- missing_evidence: AML-002, GOV-001, KYB-001, KYC-001
- findings: KYB-001, KYC-001, AML-002, GOV-001
- control_coverage_score minimum: 9

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
