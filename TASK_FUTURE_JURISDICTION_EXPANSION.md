You are working inside the Tenet repo.

Goal:
Expand Tenet beyond the current US/UK/EU scope in a pack-based way without rewriting the deterministic core.

Requirements:
1. Add future-ready jurisdiction pack scaffolds for:
   - UAE
   - Singapore
   - Hong Kong
   - Canada
   - Australia
2. Add future-ready domain pack scaffolds for:
   - fraud
   - transaction_screening
   - regulatory_licensing
   - remediation_tracking
3. Keep them structure-only:
   - metadata
   - supported audit types
   - evidence categories
   - query seeds
4. Do not invent case outcomes.
5. Do not add model logic.
6. Keep tests and loaders green.

Deliver:
- new pack files
- tests
- py_compile passing
- pytest passing
