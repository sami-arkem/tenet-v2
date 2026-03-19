You are working inside the Tenet repo.

Goal:
Extend audit memory into remediation memory so Tenet can track whether prior gaps have actually been closed over time.

Requirements:
1. Add deterministic remediation status objects per control:
   - open
   - in_progress
   - closed
   - unknown
2. Add a comparison layer for remediation status changes between audits.
3. Add tests.
4. Keep it deterministic only.
5. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
