# Immutable Audit Package

## Goal
Produce enterprise-safe export bundles that are traceable, reproducible, and tamper-evident.

## Requirements
- deterministic filenames
- export manifest
- sha256 checksums
- audit_id embedded in filenames
- export blocked if markdown changed after validation
- formatting only, never reasoning

## Outputs
- docx
- pdf
- manifest.json
