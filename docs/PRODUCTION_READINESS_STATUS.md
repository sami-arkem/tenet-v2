# Production Readiness Status

## What is now real
- canonical enums and audit context validation
- regime-map-driven audit planning
- deterministic retrieval invocation from reasoning
- control evaluation over retrieved evidence
- config-driven deployment decision
- schema-conformant structured output generation
- evidence appendix population
- test coverage for contracts, planning, decision, and reason entrypoint

## What is not fully complete yet
- control library is still MVP-scope and not a full regulatory corpus
- retrieval is deterministic lexical scoring, not yet a production-grade ranking stack
- no formal benchmark/eval harness against gold audit outcomes yet
- no LLM judge or reviewer workflow validation yet
- no ingestion-time evidence normalization for policies, procedures, and control artifacts
- no report transformation validation loop with Claude yet

## Honest gate
Do not call the reasoning brain fully production-ready until:
1. control library is expanded materially
2. reason.py passes repeatable test runs
3. retrieval quality is benchmarked
4. real model-in-the-loop audit evaluations are run
5. human review outputs are compared against expected audit decisions
