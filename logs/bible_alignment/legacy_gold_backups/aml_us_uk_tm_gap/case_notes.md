# aml_us_uk_tm_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: aml_readiness_review
- industry: fintech
- jurisdictions: US, UK
- entity_name: Real AML Case 001

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- BSA_AML
- CIP_KYC
- CDD_BO
- OFAC
- UK_MLR

## Expected control position
- missing_controls: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- missing_evidence: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- findings: KYB-001, AML-003, KYC-001, SAN-001, AML-001, AML-002, GOV-001
- control_coverage_score minimum: 15

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
