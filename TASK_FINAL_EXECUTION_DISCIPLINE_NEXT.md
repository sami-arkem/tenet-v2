You are working inside the Tenet repo.

Goal:
Harden final execution discipline so Tenet can run repeated enterprise workflows safely and reproducibly.

Requirements:
1. Add one deterministic command that runs:
   - readiness check
   - live evals
   - customer-pack stability suite
   - workflow smoke checks
   - historical reporting smoke checks
2. Add one final machine-readable summary artifact under logs/.
3. Fail loudly if any step fails.
4. Keep py_compile and pytest green.

Deliver:
- code changes
- tests if needed
- py_compile passing
- pytest passing
