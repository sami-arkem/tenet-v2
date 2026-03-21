# Eval Harness

## Purpose

The eval harness measures whether Tenet's reasoning output matches real adjudicated audit expectations.

## Design

- read real gold cases from evals/gold_cases/
- run Tenet reasoning on each case
- compare output against expected assertions
- compute weighted scores
- fail loudly when required files are missing or malformed

## Rules

- no fake gold cases
- no synthetic pass/fail benchmarks
- no hidden scoring logic
- no silent skipping of broken cases

## Current execution mode

Each case must already point at evidence that Tenet can access through the current retrieval layer.

That means gold cases should be created only after the relevant evidence has been ingested into the active retrieval corpus.

## Output

The harness writes:
- per-case scores
- assertion failures
- aggregate summary
- pass/fail status by threshold
