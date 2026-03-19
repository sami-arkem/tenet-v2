You are working inside the Tenet repo.

Goal:
Prove stable live outputs on multiple real customer evidence packs using the existing deterministic workflow.

Requirements:
1. Add 3-5 additional customer evidence packs under data/customer_evidence_packs/.
2. Cover multiple audit types and jurisdictions.
3. Run the full enterprise workflow on each:
   - intake
   - audit
   - report
   - export
   - audit memory
   - remediation memory
   - trend refresh
4. Keep model usage and runtime discipline aligned with the current stack.
5. Add a small summary script reporting:
   - pack count
   - successful workflow runs
   - failed workflow runs
6. Keep py_compile and pytest green.

Deliver:
- new customer evidence packs
- workflow outputs
- stability summary
