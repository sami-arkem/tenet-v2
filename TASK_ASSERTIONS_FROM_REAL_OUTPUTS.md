You are working inside the Tenet repo.

Goal:
Turn the 10 newly generated real deterministic gold-case outputs into strict gold assertions and reviewer notes.

Requirements:
1. Read each evals/gold_cases/*/initial_run_output.json for the 10 new cases.
2. Write:
   - expected_assertions.json
   - case_notes.md
3. Use actual observed deterministic outputs only.
4. Do not invent strong-pass outcomes.
5. Keep coverage minimums aligned to real observed behavior.
6. Keep decisions/regimes/findings/missing control IDs grounded in the current corpus behavior.

Deliver:
- 10 completed expected_assertions.json files
- 10 completed case_notes.md files
- rerun live eval summary after adding them
