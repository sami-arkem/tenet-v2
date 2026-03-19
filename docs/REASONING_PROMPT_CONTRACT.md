# Reasoning Prompt Contract

The reasoning prompt must tell the model:

1. what Tenet is doing
2. what audit is in scope
3. which regimes and controls apply
4. what evidence was retrieved
5. what schema it must fill
6. what it must not do

## Required inputs

- audit_context
- audit_plan
- retrieved_chunks
- output_schema_template

## Required behavior

- reason from provided evidence only
- do not claim facts not grounded in retrieved evidence
- distinguish missing control from missing evidence
- preserve citations
- produce valid JSON only
- never add fields outside the output contract

## Style

- precise
- regulator-ready
- boardroom-ready
- not verbose
- not speculative
