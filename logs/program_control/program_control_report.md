# Tenet Program Control Report

- generated_at_epoch: `1773819225`
- enterprise_readiness_score: `70.62`

## Score Breakdown

- proof_density_score: `13.62`
- bible_alignment_score: `25.0`
- workflow_integrity_score: `20.0`
- customer_pack_stability_score: `2.0`
- taxonomy_closure_score: `10.0`
- intake_throughput_score: `0.0`
- total_score: `70.62`

## Metrics

### proof_density
- present: `True`
- gold_actual: `52`
- gold_target: `100`
- packs_actual: `6`
- packs_target: `20`
- gate_green: `True`

### final_execution
- present: `True`
- all_steps_passed: `True`

### live_eval
- present: `True`
- case_count: `52`
- failed_count: `0`
- min_weighted_score: `1.0`

### customer_pack_summary
- present: `True`
- successful_runs: `4`

### bible_alignment
- present: `True`
- status: `green`
- issue_count: `0`
- error_count: `0`
- warning_count: `0`
- taxonomy_issue_count: `0`

### taxonomy
- dossiers_present: `True`
- dossier_count: `7`
- adjudications_applied: `7`
- unresolved_dossiers: `0`

### real_002
- readiness_present: `True`
- ready_items: `0`
- blocked_items: `11`
- blocker_type_counts: `{'assertions_semantics': 8, 'audit_context_semantics': 44, 'missing_required': 22, 'placeholder': 52}`
- imported_shards: `0`
- failed_shards: `0`

## Blockers

- [high] `proof.gold_cases_below_target` - Gold cases below target: 52/100
  - detail: Proof density is not yet at the required corpus breadth.
  - action: Keep importing real corpus-backed gold cases until 100 is reached.
- [high] `proof.customer_packs_below_target` - Customer packs below target: 6/20
  - detail: Enterprise workflow proof is not yet broad enough.
  - action: Add and stabilize more real customer evidence packs until 20 is reached.
- [medium] `intake.real_002_blocked_items_present` - Blocked intake items in real_002: 11
  - detail: The current next proof batch is not yet importable.
  - action: Use repair files and blocker reports to convert blocked items into ready items.

## Worklist

1. Convert blocked real_002 intake items into ready items
   - why: Proof throughput is currently constrained by blocked intake.
   - exact_output: Reduce blocked_items to 0 or at least produce a non-empty ready-only manifest.
2. Import the next real gold-case batch
   - why: Gold proof corpus is below target.
   - exact_output: Move from 52 toward 100 gold cases without breaking gates.
3. Import the next customer-pack batch
   - why: Enterprise operator proof is below target.
   - exact_output: Move from 6 toward 20 customer packs with green stability.
4. Rerun proof-density + final execution after every corpus change
   - why: Current truth must stay authoritative and regression-free.
   - exact_output: Keep proof-density green and final execution green every run.
