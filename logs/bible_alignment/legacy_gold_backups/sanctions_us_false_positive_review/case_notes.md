# sanctions_us_false_positive_review

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: sanctions_readiness_review
- industry: payments
- jurisdictions: US
- entity_name: Real US False Positive Review Case

## Human adjudication
Expected outcome is CONDITIONALLY_APPROVED based on the current corpus-backed deterministic output.

## Expected regimes
- OFAC

## Expected control position
- missing_controls: GOV-001, SAN-001
- missing_evidence: GOV-001, SAN-001
- findings: SAN-001, GOV-001
- control_coverage_score minimum: 35

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
