# Historical Context Integration

## Goal
Inject deterministic historical context into Tenet's live audit flow so current audits can reference prior recurring weaknesses and prior remediation progress for the same entity.

## Principles
- deterministic only
- no model dependency
- historical context is advisory, never authoritative
- current audit truth always wins
- historical context may enrich retrieval preparation and audit context, but must not overwrite current findings, controls, or decisions

## Historical fields
- prior recurring missing controls
- prior recurring findings
- prior decision trajectory
- prior remediation trajectory

## Integration points
- entity-name based trend lookup
- runtime retrieval preparation
- retrieval query enrichment
- optional report-pack visibility later

## Non-negotiable
Historical context must never override the current audit's decision, findings, or missing controls.
