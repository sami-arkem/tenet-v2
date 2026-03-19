# Pack Composition Layer

## Goal
Turn jurisdiction packs + domain packs into a deterministic composition layer that Tenet can use during audit planning and retrieval preparation.

## Why
Packs on disk are not enough.
Tenet must be able to compose:
- jurisdictions
- domains
- regimes
- controls
- evidence categories
- retrieval query seeds

## Rules
- deterministic only
- no model dependency
- reusable across future domains and jurisdictions
- no hardcoded one-off audit logic in the composition layer

## Output
A normalized composition object containing:
- jurisdictions
- domains
- regimes
- controls
- evidence_categories
- query_seeds
