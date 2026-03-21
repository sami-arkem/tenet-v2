# Operator Task: aml_hong_kong_case_001

- batch_label: `proof_batch_real_002`
- status: `blocked`
- readiness_score: `0.6`
- kind: `gold_case`
- title: `AML Hong Kong case 001`
- source_dir: `intake/proof_batch_real_002/aml_hong_kong_case_001`
- domains: `aml`
- jurisdictions: `hong_kong`
- reason: `zero_coverage`

## Required completion work

- no missing required files
- fix validation error: `audit_context.json::empty_audit_type`
- fix validation error: `audit_context.json::empty_industry`
- fix validation error: `audit_context.json::missing_source_families`
- fix validation error: `audit_context.json::missing_query_terms`
- fix validation error: `expected_assertions.json::no_meaningful_expected_values`
- remove placeholder content: `README.md::placeholder`
- remove placeholder content: `audit_context.json::placeholder`
- remove placeholder content: `case_notes.md::placeholder`
- remove placeholder content: `notes.md::placeholder`

## Non-negotiables

- real corpus only
- deterministic current audit truth only
- do not invent pass outcomes
- do not let historical context override current truth
- do not change taxonomy to make the item pass

