You are working inside the Tenet repo.

Goal:
Integrate deterministic historical context into Tenet's audit flow so current audits can reference prior recurring weaknesses and prior remediation progress for the same entity.

Requirements:
1. Add a deterministic lookup from entity_name to trend summary.
2. Inject historical context into runtime preparation only when available.
3. Add fields such as:
   - prior recurring missing controls
   - prior recurring findings
   - prior decision trajectory
   - prior remediation trajectory
4. Keep this deterministic only.
5. Do not let historical context override current audit truth.
6. Add tests.
7. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
