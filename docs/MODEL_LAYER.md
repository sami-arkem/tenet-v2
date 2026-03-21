# Model Layer

## Purpose

The model layer is the controlled interface between Tenet and frontier models.

It exists to:
- centralize provider access
- enforce structured JSON generation
- keep prompting consistent
- separate model orchestration from reasoning logic

## Rules

- model calls must go through src/llm/model_adapter.py
- reasoning prompts must be built in src/reasoning/prompt_builder.py
- reasoning outputs must be JSON-first
- deterministic code remains source of truth for validation and decision rules

## Separation of responsibilities

### model adapter
- provider selection
- config loading
- request shaping
- response parsing
- JSON enforcement
- hard failure on malformed structured output

### reasoning prompt builder
- build system prompt
- build user payload
- attach audit context
- attach audit plan
- attach retrieved evidence
- attach output contract
- constrain model behavior

## Non-goal

The model layer must not silently invent unsupported schema fields or bypass deterministic validation.
