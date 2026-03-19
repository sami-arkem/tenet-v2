You are working inside the Tenet repo.

Goal:
Integrate the deterministic pack composition layer into the main Tenet audit flow so future domains and jurisdictions are first-class citizens.

Requirements:
1. Use pack composition during audit planning and retrieval preparation.
2. Do not break existing gold cases.
3. Keep deterministic core authoritative.
4. Keep model usage at zero for this task.
5. Add tests for:
   - AML US path
   - sanctions US/EU path
   - vendor global path
6. Keep py_compile and pytest green.

Deliver:
- integration changes
- tests
- py_compile passing
- pytest passing
