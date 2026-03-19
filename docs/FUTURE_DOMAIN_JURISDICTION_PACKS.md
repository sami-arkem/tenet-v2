# Future Domain / Jurisdiction Packs

## Goal
Turn Tenet into a reusable compliance intelligence engine across domains and jurisdictions without rewriting core logic.

## Principles
- structure first
- deterministic only
- no model dependency
- stable IDs
- jurisdiction packs and domain packs stay independent
- audit logic composes packs together

## Current jurisdictions
- US
- UK
- EU

## Current domains
- aml
- kyc_kyb
- sanctions
- governance
- vendor_risk

## Expansion-ready domains
- screening
- regulatory_reporting

## Rule
Packs may define:
- metadata
- supported audit types
- regimes
- controls
- evidence categories
- query seeds

They must not contain invented case outcomes.
