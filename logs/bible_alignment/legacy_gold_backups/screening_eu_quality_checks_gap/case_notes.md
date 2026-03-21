# screening_eu_quality_checks_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: transaction_screening_review
- industry: crypto
- jurisdictions: EU
- entity_name: Real EU Screening Quality Gap

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- EU_SANCTIONS

## Expected control position
- missing_controls: AML-003, GOV-001, SAN-001
- missing_evidence: AML-003, GOV-001, SAN-001
- findings: AML-003, SAN-001, GOV-001
- control_coverage_score minimum: 12

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
