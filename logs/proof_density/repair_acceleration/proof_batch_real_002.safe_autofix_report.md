# Proof Intake Safe Autofix Report

- generated_at_epoch: `1773818644`
- mode: `write`
- entry_count: `11`
- changed_count: `11`
- blocked_count: `11`
- workspace_changed: `True`

## aml_australia_pack_001

- kind: `customer_pack`
- source_dir: `intake/proof_batch_real_002/aml_australia_pack_001`
- changed: `True`
- blocked: `True`
- backup_dir: `None`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - synchronized files_present[audit_context.json]=True
- mutations:
  - `intake/proof_batch_real_002/aml_australia_pack_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True`

## aml_canada_pack_001

- kind: `customer_pack`
- source_dir: `intake/proof_batch_real_002/aml_canada_pack_001`
- changed: `True`
- blocked: `True`
- backup_dir: `None`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - synchronized files_present[audit_context.json]=True
- mutations:
  - `intake/proof_batch_real_002/aml_canada_pack_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True`

## aml_eu_pack_001

- kind: `customer_pack`
- source_dir: `intake/proof_batch_real_002/aml_eu_pack_001`
- changed: `True`
- blocked: `True`
- backup_dir: `None`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - synchronized files_present[audit_context.json]=True
- mutations:
  - `intake/proof_batch_real_002/aml_eu_pack_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True`

## aml_canada_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_canada_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_canada_case_001_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_canada_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_canada_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_canada_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## aml_eu_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_eu_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_eu_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_eu_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_eu_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_eu_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## aml_global_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_global_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_global_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_global_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_global_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_global_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## aml_hong_kong_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_hong_kong_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_hong_kong_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_hong_kong_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_hong_kong_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_hong_kong_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## aml_india_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_india_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_india_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_india_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_india_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_india_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## aml_singapore_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/aml_singapore_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/aml_singapore_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/aml_singapore_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/aml_singapore_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/aml_singapore_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## fraud_canada_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/fraud_canada_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/fraud_canada_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/fraud_canada_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/fraud_canada_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/fraud_canada_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## fraud_eu_case_001

- kind: `gold_case`
- source_dir: `intake/proof_batch_real_002/fraud_eu_case_001`
- changed: `True`
- blocked: `True`
- backup_dir: `logs/proof_density/repair_acceleration/safe_autofix_backups/fraud_eu_case_001`
- reasons:
  - placeholders still present: 2
  - left operator_fill_status.placeholder_free=false because placeholders remain
  - left operator_fill_status.ready_for_import=false because blockers remain
  - left operator_fill_status.real_sources_attached=false because real source metadata is incomplete
  - audit_type still missing after safe autofix
  - industry still missing after safe autofix
  - source_families/query_terms still incomplete after safe autofix
  - left operator_fill_status.ready_for_import=false because semantic blockers remain
  - expected has no meaningful values; left unresolved
  - trimmed case_notes whitespace
  - synchronized files_present[audit_context.json]=True
  - synchronized files_present[expected_assertions.json]=True
  - synchronized files_present[case_notes.md]=True
- mutations:
  - `intake/proof_batch_real_002/fraud_eu_case_001/audit_context.json` changed=`False` reason=`left operator_fill_status.placeholder_free=false because placeholders remain; left operator_fill_status.ready_for_import=false because blockers remain; left operator_fill_status.real_sources_attached=false because real source metadata is incomplete; audit_type still missing after safe autofix; industry still missing after safe autofix; source_families/query_terms still incomplete after safe autofix; left operator_fill_status.ready_for_import=false because semantic blockers remain`
  - `intake/proof_batch_real_002/fraud_eu_case_001/expected_assertions.json` changed=`False` reason=`expected has no meaningful values; left unresolved`
  - `intake/proof_batch_real_002/fraud_eu_case_001/case_notes.md` changed=`True` reason=`trimmed case_notes whitespace`
  - `repair_workspace.json::operator_repair` changed=`True` reason=`synchronized files_present[audit_context.json]=True; synchronized files_present[expected_assertions.json]=True; synchronized files_present[case_notes.md]=True`

## Verifier Result

- passed: `True`
- returncode: `0`
- duration_seconds: `0.09`

