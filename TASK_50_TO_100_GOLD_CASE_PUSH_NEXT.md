You are working inside the Tenet repo.

Goal:
Push Tenet from the current benchmark toward the 50-100 gold case readiness band.

Requirements:
1. Add the next 12-20 real corpus-backed gold cases.
2. Cover:
   - AML
   - KYC/KYB
   - sanctions
   - governance
   - vendor risk
   - fraud
   - transaction screening
   - regulatory licensing
   - remediation tracking
3. Use the current deterministic engine only for case creation.
4. Write:
   - audit_context.json
   - initial_run_output.json
   - expected_assertions.json from observed outputs
   - case_notes.md
5. Rerun live evals after each batch.
6. Keep py_compile and pytest green.

Deliver:
- new gold cases
- updated live eval summary
- readiness improvement toward the 50-100 band
