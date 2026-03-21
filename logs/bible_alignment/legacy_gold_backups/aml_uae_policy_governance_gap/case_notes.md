# aml_uae_policy_governance_gap

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: aml_readiness_review
- industry: payments
- jurisdictions: UAE
- entity_name: Real UAE AML Policy Governance Gap
- domains: aml, governance

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- UAE_AML_BASELINE
- UAE_SANCTIONS_BASELINE
- UAE_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- missing_evidence: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- findings: KYB-001, AML-003, KYC-001, SAN-001, AML-001, AML-002, GOV-001
- control_coverage_score minimum: 15

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
