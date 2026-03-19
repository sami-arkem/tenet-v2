You are working inside the Tenet repo.

Goal:
Add the next 10 real global gold cases across future jurisdictions and future domains using the existing deterministic pack system.

Requirements:
1. Add 10 new real corpus-backed cases across:
   - UAE
   - Singapore
   - Hong Kong
   - Canada
   - Australia
2. Cover at least:
   - fraud
   - transaction_screening
   - regulatory_licensing
   - remediation_tracking
3. For each case:
   - write audit_context.json
   - run deterministic output first
   - write expected_assertions.json from observed output
   - write case_notes.md
4. Keep model usage at zero during case creation.
5. Rerun full live eval suite afterward.

Deliver:
- 10 new gold-case folders
- deterministic outputs
- strict assertions
- updated live eval summary
