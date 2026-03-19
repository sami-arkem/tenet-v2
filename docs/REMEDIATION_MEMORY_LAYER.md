# Remediation Memory Layer

## Goal
Extend Tenet's deterministic audit memory into remediation memory so the platform can track whether prior gaps are still open, moving, or closed over time.

## Why
A compliance intelligence platform cannot stop at finding gaps.
It must remember:
- which controls were open before
- which controls remain open
- which controls appear to be moving toward closure
- which controls have been closed between audits

## Principles
- deterministic only
- no model dependency
- based on locked audit outputs and audit memory
- human-reviewable JSON
- append-only snapshots
- comparison is rule-based and reproducible

## Deterministic remediation statuses
- open
- in_progress
- closed
- unknown

## Status rules
Within a single audit snapshot:
- control in missing_controls => open
- control in findings but not in missing_controls => in_progress
- anything else => unknown

Across two snapshots:
- prior open/in_progress and absent in current => closed
- present in both => use current snapshot status
- newly present in current => use current snapshot status

## Snapshot fields
- audit_id
- entity_name
- audit_type
- jurisdictions
- domains
- remediation_status_by_control
- deployment_decision

## Comparison fields
- prior_audit_id
- current_audit_id
- entity_name
- status_changes
- newly_closed_controls
- newly_open_controls
- still_open_controls
- improved_controls
- unchanged_controls
