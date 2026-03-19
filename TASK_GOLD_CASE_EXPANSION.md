You are working inside the Tenet repo.

Goal:
Expand the real gold-case benchmark beyond 8 cases using the existing retrieval corpus and deterministic audit engine.

Requirements:
1. Add 10 additional real gold-case folders across:
   - AML
   - KYC/KYB
   - sanctions
   - governance
   - vendor
2. Each case must include:
   - audit_context.json
   - expected_assertions.json
   - case_notes.md
3. Use existing corpus behavior, not invented strong-pass fantasies.
4. Add at least:
   - one false-positive style case
   - one partial-evidence case
   - one governance-heavy case
   - one vendor-heavy case
5. Keep model usage at zero for case creation.
6. Deliver deterministic outputs first, then assertions.

Deliver:
- new gold-case folders
- deterministic run outputs
- updated live eval summary
