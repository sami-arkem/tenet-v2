# Repair File: aml_india_case_001

- batch_label: `proof_batch_real_002`
- kind: `gold_case`
- title: `AML India case 001`
- source_dir: `intake/proof_batch_real_002/aml_india_case_001`
- domains: `aml`
- jurisdictions: `india`
- reason: `zero_coverage`
- current_ready: `False`
- current_readiness_score: `0.6`

## Repair Actions

1. [audit_context_semantics] audit_context.json::empty_audit_type
   - fix: set audit_type to the real audit type used by Tenet for this corpus-backed item
2. [audit_context_semantics] audit_context.json::empty_industry
   - fix: set industry to the real industry under audit
3. [missing_required] audit_context.json::missing_source_families
   - fix: add one or more real source_families grounded in the corpus
4. [missing_required] audit_context.json::missing_query_terms
   - fix: add real retrieval query_terms grounded in the corpus
5. [assertions_semantics] expected_assertions.json::no_meaningful_expected_values
   - fix: add real expected.equals, expected.contains, or expected.minimums values from observed deterministic output
6. [placeholder] README.md::placeholder
   - fix: remove placeholder text and replace it with real intake content
7. [placeholder] audit_context.json::placeholder
   - fix: remove placeholder text and replace it with real intake content
8. [placeholder] case_notes.md::placeholder
   - fix: remove placeholder text and replace it with real intake content
9. [placeholder] notes.md::placeholder
   - fix: remove placeholder text and replace it with real intake content
10. [audit_context_semantics] audit_context.json::operator_fill_status_real_sources_attached_must_be_true
   - fix: set operator_fill_status flags to true only after real sources are attached and placeholders are removed
11. [placeholder] audit_context.json::operator_fill_status_placeholder_free_must_be_true
   - fix: set operator_fill_status flags to true only after real sources are attached and placeholders are removed
12. [audit_context_semantics] audit_context.json::operator_fill_status_ready_for_import_must_be_true
   - fix: set operator_fill_status flags to true only after real sources are attached and placeholders are removed

## Non-negotiables

- real corpus only
- do not invent pass outcomes
- deterministic current audit truth is authoritative
- historical context must never override current truth
- do not weaken the importer contract or gates
