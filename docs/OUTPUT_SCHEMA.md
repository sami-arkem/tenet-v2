# Tenet Output Schema

This is the master enterprise output contract for Tenet.

## Purpose
The reasoning layer must always output structured audit JSON in this shape before Claude transforms it into a world-class report.

## Required top-level sections
- audit_meta
- entity_profile
- audit_scope
- regulatory_applicability
- executive_summary
- deployment_decision
- financial_exposure
- control_assessment
- findings
- key_risks
- missing_controls
- missing_evidence
- remediation_roadmap
- confidence_assessment

## Optional but premium sections
- reporting_outputs
- evidence_appendix

## Rules
1. No final answer without findings.
2. No finding without severity.
3. No major finding without citations.
4. No deployment decision without rationale.
5. No financial exposure without assumptions.
6. Human review remains required for MVP.
7. Claude is the report-polish layer, not the primary reasoning layer.

## Status values
Deployment decision:
- APPROVED
- CONDITIONALLY_APPROVED
- BLOCKED

Control status:
- ADEQUATE
- PARTIAL
- INADEQUATE
- NOT_EVIDENCED

Evidence quality:
- STRONG
- MODERATE
- WEAK
- NONE

Confidence level:
- HIGH
- MODERATE
- LOW
