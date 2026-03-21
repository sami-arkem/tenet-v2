# Operator Task: aml_australia_pack_001

- batch_label: `proof_batch_real_002`
- status: `blocked`
- readiness_score: `0.6`
- kind: `customer_pack`
- title: `AML Australia pack 001`
- source_dir: `intake/proof_batch_real_002/aml_australia_pack_001`
- domains: `aml`
- jurisdictions: `australia`
- reason: `zero_coverage`

## Required completion work

- no missing required files
- fix validation error: `audit_context.json::empty_audit_type`
- fix validation error: `audit_context.json::empty_industry`
- fix validation error: `audit_context.json::missing_source_families`
- fix validation error: `audit_context.json::missing_query_terms`
- remove placeholder content: `README.md::placeholder`
- remove placeholder content: `audit_context.json::placeholder`
- remove placeholder content: `notes.md::placeholder`

## Non-negotiables

- real corpus only
- deterministic current audit truth only
- do not invent pass outcomes
- do not let historical context override current truth
- do not change taxonomy to make the item pass

