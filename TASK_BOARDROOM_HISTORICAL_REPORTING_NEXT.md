You are working inside the Tenet repo.

Goal:
Expose deterministic historical context in report-pack generation so board and regulator reports can reference repeated weaknesses and remediation direction without changing current audit truth.

Requirements:
1. Add historical context fields into the report pack.
2. Keep them clearly labeled as prior/historical context.
3. Do not let historical context alter current deployment decision or current findings.
4. Add tests.
5. Keep py_compile and pytest green.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
