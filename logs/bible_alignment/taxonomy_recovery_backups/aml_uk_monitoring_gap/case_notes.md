# aml_uk_monitoring_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: aml_readiness_review
- industry: payments
- jurisdictions: UK
- entity_name: Real AML UK Monitoring Gap Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- UK_MLR

## Expected control position
- missing_controls: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- missing_evidence: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- findings: KYB-001, AML-003, KYC-001, SAN-001, AML-001, AML-002, GOV-001
- control_coverage_score minimum: 15

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
