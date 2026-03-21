# Enterprise Workflow Plan

## Goal
Make Tenet run as a real enterprise workflow:

intake -> audit -> report -> export -> memory -> remediation tracking

## Launch readiness gates
Tenet is operationally closer to launch when these are true:
1. 50-100 strong gold cases across domains and jurisdictions
2. stable live outputs on real customer evidence packs
3. clear enterprise workflow from intake to remediation tracking

## Rules
- deterministic audit core remains authoritative
- model is used only where already approved in the stack
- evidence packs must be human-reviewable
- workflow outputs must be reproducible
- exports must be validation-gated
- memory writes must happen only from locked audit outputs

## Workflow outputs per run
- locked audit JSON
- report markdown bundle
- validated export bundle
- audit memory snapshot
- remediation memory snapshot
- optional trend summary refresh

## Customer evidence pack structure
Each pack must contain:
- audit_context.json
- optional notes.md
- optional source inventory files
