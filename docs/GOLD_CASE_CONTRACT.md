# Gold Case Contract

Gold cases must be based on real evidence packs and real human-adjudicated expected outcomes.

## Directory shape

Each gold case lives at:

evals/gold_cases/<case_id>/

Required files:
- audit_context.json
- expected_assertions.json
- case_notes.md

Optional files:
- evidence_manifest.json
- adjudication_notes.md

## Required principle

No synthetic gold cases.
No invented expected outcomes.
No placeholder evidence references.

## audit_context.json

This must be a valid Tenet reasoning input object.

## expected_assertions.json

Supported fields:

- case_id
- expected:
  - equals
  - contains
  - minimums

### equals
Exact value match.

Example:
{
  "deployment_decision.status": "BLOCKED"
}

### contains
Expected subset presence.

Example:
{
  "regulatory_applicability.primary_regimes": ["BSA_AML", "UK_MLR"],
  "missing_controls.control_id": ["AML-003", "SAN-001"]
}

### minimums
Numeric floors.

Example:
{
  "control_assessment.control_coverage_score": 40
}

## case_notes.md

Must explain:
- what the entity is
- what evidence corpus this case depends on
- why the expected outcome is correct
- who adjudicated it

## Gold standard

A case is only valid when a human reviewer would defend its expected outcome in front of:
- a client
- an internal QA reviewer
- a regulator
