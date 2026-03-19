You are working inside the Tenet repo.

Goal:
Add deterministic audit memory so Tenet can compare entities, findings, and remediation states across prior audits.

Requirements:
1. Add an audit memory store format:
   - audit_id
   - entity_name
   - jurisdictions
   - domains
   - deployment_decision
   - findings control_ids
   - missing_controls control_ids
   - remediation roadmap summary
2. Add a write path from completed audit outputs into memory snapshots.
3. Add a compare function:
   - prior vs current findings
   - newly introduced gaps
   - closed gaps
   - unchanged gaps
4. Keep it deterministic only.
5. Add tests.
6. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
