# Trend Intelligence Layer

## Goal
Turn Tenet's deterministic audit memory and remediation memory into reusable institutional intelligence.

## What this layer must do
- detect recurring missing controls
- detect recurring findings
- summarize decision trajectory over time
- summarize remediation improvement trajectory
- generate entity-level deterministic governance/screening/licensing/remediation weakness summaries

## Principles
- deterministic only
- no model dependency
- human-reviewable JSON
- derived only from locked audit/remediation memory
- stable comparison logic
- no invented conclusions

## Outputs
Per entity trend files containing:
- audit history summary
- recurring missing controls
- recurring findings
- repeated governance weaknesses
- repeated screening weaknesses
- repeated licensing weaknesses
- repeated remediation weaknesses
- decision trajectory
- remediation improvement trajectory
