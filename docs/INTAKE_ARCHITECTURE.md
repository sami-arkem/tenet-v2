# Intake Architecture

## Objective

Tenet intake should feel like an AI-led discovery session while producing strict backend structure for reasoning.

## Layers

### 1. Conversational orchestration layer
Responsible for:
- greeting
- asking the next best question
- reflecting understanding
- maintaining tone
- guiding the user without feeling like a form

### 2. Intake state layer
Responsible for:
- tracking known fields
- tracking missing fields
- tracking confidence
- tracking evidence inventory
- tracking uncertainty and contradictions

### 3. Normalization layer
Responsible for:
- mapping free text to canonical enums
- extracting entities, jurisdictions, products, customer types, and risk clues
- generating the reasoning-ready audit context

### 4. Reasoning handoff layer
Responsible for:
- validating normalized audit context
- producing final reasoning input
- invoking Tenet reasoning

## UX principles

- conversation first
- structure underneath
- zero wasted questions
- calm, credible, slightly witty
- always moving toward audit readiness

## Engineering principles

- deterministic normalization first
- config-driven heuristics where possible
- model-assisted orchestration later
- strict contracts before UI polish
