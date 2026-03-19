# Gold Case Build Process

## Rule
Only create gold cases from real evidence already available to the Tenet retrieval corpus.

## Required inputs
- real audit context
- real evidence corpus already ingested
- human adjudicated expected result
- written adjudication notes

## Build steps
1. identify one real audit scenario
2. confirm its evidence exists in the active retrieval corpus
3. write audit_context.json
4. run Tenet once and inspect output
5. manually adjudicate the correct expected result
6. write expected_assertions.json
7. write case_notes.md with rationale
8. run eval suite
9. inspect failures
10. improve system only after reviewing failure causes

## Minimum adjudication fields
- expected deployment decision
- expected primary regimes
- expected missing controls
- expected missing evidence
- expected findings or findings domains

## Hard rule
No guessed assertions.
No synthetic evidence references.
No placeholder gold cases.
