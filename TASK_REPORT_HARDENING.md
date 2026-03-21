You are working inside the Tenet repo.

Goal:
Harden the report layer so Tenet can produce premium regulator-ready and board-ready reports from locked audit JSON without drift.

Requirements:
1. Add a repair/retry loop in report_transformer.py:
   - first generate report
   - validate with report_validator
   - if validation fails, run one repair pass with the validation failures fed back to the model
   - fail loudly if second pass still fails

2. Add report section templates:
   - board memo template
   - regulator memo template
   - client report template
   Keep them deterministic in structure and model-filled in wording only.

3. Add tests:
   - validator catches missing finding titles
   - repair loop succeeds when first draft omits required finding/control references
   - repair loop fails loudly after second invalid draft

4. Do not weaken audit truth.
5. Do not let the model change deployment decision or findings.
6. Keep model cost low and use gpt-4.1-mini.

Deliver:
- code changes
- tests
- py_compile passing
- pytest passing
