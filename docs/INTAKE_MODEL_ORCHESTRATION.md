# Intake Model Orchestration

## Purpose

This layer makes Tenet intake feel like an elite AI compliance strategist while preserving deterministic backend structure.

## Architecture

1. deterministic intake state and normalization
2. AI prompt builder
3. model-backed follow-up generation
4. strict validation of returned question object
5. fallback to deterministic selector if model output is invalid

## Non-negotiable rule

The model may shape the conversational experience, but it may not invent the backend schema.

The deterministic layer remains the source of truth for:
- canonical fields
- readiness for reasoning
- reasoning handoff object

## Output contract

The model must return JSON only:

{
  "assistant_opening": "string",
  "understanding_summary": "string",
  "confidence_line": "string",
  "next_question": "string",
  "why_this_matters": "string",
  "question_key_guess": "string"
}

## Safety

If model output is malformed or low quality:
- discard it
- use deterministic question selector
