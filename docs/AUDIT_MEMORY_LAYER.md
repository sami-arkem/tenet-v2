# Audit Memory Layer

## Goal
Give Tenet a deterministic audit memory so prior audits can be stored, compared, and reused without adding model risk.

## Why
Tenet must improve over time.
That requires:
- preserving prior audit states
- tracking changes in findings and missing controls
- detecting newly introduced gaps
- detecting closed gaps
- comparing deployment decisions over time

## Principles
- deterministic only
- no model dependency
- append-only snapshots
- human-reviewable JSON
- stable comparison rules
- no mutation of audit truth

## Required snapshot fields
- audit_id
- entity_name
- jurisdictions
- domains
- audit_type
- deployment_decision
- findings control_ids
- missing_controls control_ids
- missing_evidence control_ids or titles
- remediation roadmap summary

## Comparison outputs
- prior_audit_id
- current_audit_id
- entity_name
- prior_decision
- current_decision
- newly_introduced_gaps
- closed_gaps
- unchanged_gaps
- newly_introduced_findings
- closed_findings
- unchanged_findings
