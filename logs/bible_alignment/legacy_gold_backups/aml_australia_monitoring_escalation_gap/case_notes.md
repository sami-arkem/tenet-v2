# aml_australia_monitoring_escalation_gap

## Scenario
Real corpus-backed gold case.

## Audit context
- audit_type: aml_readiness_review
- industry: payments
- jurisdictions: AUSTRALIA
- entity_name: Real Australia AML Monitoring Escalation Gap
- domains: aml, governance, regulatory_reporting

## Human adjudication
Expected outcome is BLOCKED based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
- AU_AML_BASELINE
- AU_SANCTIONS_BASELINE
- AU_GOVERNANCE_BASELINE

## Expected control position
- missing_controls: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- missing_evidence: AML-001, AML-002, AML-003, GOV-001, KYB-001, KYC-001, SAN-001
- findings: KYB-001, AML-003, KYC-001, SAN-001, AML-001, AML-002, GOV-001
- control_coverage_score minimum: 15

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
