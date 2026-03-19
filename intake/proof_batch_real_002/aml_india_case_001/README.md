# Intake Workspace: aml_india_case_001

- title: `AML India case 001`
- kind: `gold_case`
- domains: `aml`
- jurisdictions: `india`
- reason: `zero_coverage`

## Required files

- `audit_context.json`
- `expected_assertions.json`
- `case_notes.md`

## Optional files

- `evidence_index.json`
- `source_manifest.json`
- `notes.md`

## Rules

- real corpus only
- no placeholders
- no invented outcomes
- deterministic current audit truth remains authoritative
- historical context must never override current truth

## Ready criteria

- all required files exist
- audit_context.json matches the strict importer contract
- expected_assertions.json matches the strict gold-case contract
- no placeholder markers in text/json/md files
- source_families and query_terms are real and non-empty

