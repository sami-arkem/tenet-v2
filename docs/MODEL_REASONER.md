# Model Reasoner

## Purpose

The model reasoner is the controlled bridge between:
- deterministic audit planning and retrieval
- frontier model structured reasoning
- schema-safe Tenet outputs

## Responsibilities

- build reasoning prompt
- call model adapter
- validate returned JSON against the output contract
- repair missing or malformed sections conservatively
- reject unsupported structure
- return schema-safe structured output

## Rules

- model reasoner must never bypass schema validation
- model reasoner must never trust model output blindly
- missing evidence and missing controls must remain separate
- deterministic fields may be injected after repair when needed
- final result must always conform to the locked output schema

## Flow

1. receive audit_context, audit_plan, retrieved_chunks
2. build prompt
3. call model
4. validate structure
5. repair structure
6. validate repaired output
7. return schema-safe JSON
