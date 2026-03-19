You are working inside the Tenet repo.

Goal:
Expand the deterministic control and regime library so Tenet becomes a reusable audit engine across AML, KYC/KYB, sanctions, governance, vendor, and future domains.

Requirements:
1. Add deterministic control-library packs for:
   - AML governance
   - customer identification / CIP
   - KYB / beneficial ownership
   - sanctions screening and escalation
   - governance baseline
   - vendor / third-party oversight
2. Add regime-library organization by:
   - US
   - UK
   - EU
3. Add tests that verify each audit type maps to a non-empty control set where appropriate.
4. Keep control IDs stable and human-readable.
5. Do not add fake data; only structure, mappings, and deterministic code changes.
6. Keep model usage at zero for this task.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
