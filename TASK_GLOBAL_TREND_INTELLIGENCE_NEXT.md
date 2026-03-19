You are working inside the Tenet repo.

Goal:
Add deterministic trend intelligence on top of audit memory and remediation memory so Tenet can summarize recurring gaps and multi-audit risk trajectories per entity.

Requirements:
1. Add trend aggregation for:
   - recurring missing controls
   - recurring findings
   - decision trajectory over time
   - remediation improvement trajectory
2. Add entity-level summary generation:
   - repeated governance weaknesses
   - repeated screening weaknesses
   - repeated licensing/remediation weaknesses
3. Keep it deterministic only.
4. Add tests.
5. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
