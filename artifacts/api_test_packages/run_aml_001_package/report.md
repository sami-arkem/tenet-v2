# Tenet Deterministic Audit Report: run_aml_001

Generated: 2026-03-19T17:59:43.784297+00:00

## Executive Summary

- Company: Acme Fintech
- Industry: fintech
- Primary jurisdiction: uk
- Audit type: aml_readiness_review
- Domains: aml
- Jurisdictions: uk, eu
- Overall posture: AMBER
- Deployment decision: CONDITIONALLY_APPROVED
- Summary: Deterministic audit completed with posture=AMBER, decision=CONDITIONALLY_APPROVED, controls=1, passed=0, partial=1, failed=0, missing_evidence=0.

## Deterministic Guardrails

- Current audit truth is authoritative.
- Historical context is included only as prior context and never overrides current truth.
- Findings below are evidence-grounded and control-specific.

## Control Evaluations

### AML.MONITORING.001 (UK_MLR.001)
- Verdict: PARTIAL
- Evidence coverage ratio: 0.5
- Rationale: Control present but evidence coverage is incomplete.
- Evidence refs:
  - Monitoring Policy — policy.pdf#L1-L20

## Findings

### AML.MONITORING.001::finding
- Control: AML.MONITORING.001
- Regime: UK_MLR.001
- Severity: HIGH
- Status: OPEN
- Verdict: PARTIAL
- Description: Deterministic evaluation found verdict=PARTIAL for control AML.MONITORING.001.
- Rationale: Control present but evidence coverage is incomplete.
- Missing evidence types: monitoring_report
- Evidence refs:
  - Monitoring Policy — policy.pdf#L1-L20
- Remediation actions:
  - Provide evidence covering missing evidence types: monitoring_report.

## Remediation Plan

### remediation::0001
- Finding: AML.MONITORING.001::finding
- Owner: compliance@acme.com
- Status: OPEN
- Action required: Provide evidence covering missing evidence types: monitoring_report.

## Prior / Historical Context

- prior_findings: 2

## Readiness Statement

The system is not fully ready; remediation is required before clean approval.
