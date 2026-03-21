# Audit Planning Layer

## Purpose

The audit planning layer is the deterministic bridge between intake and reasoning.

It converts audit context into a structured review plan before the model generates findings.

This layer exists to prevent freeform reasoning directly from retrieved chunks into enterprise outputs.

## Goals

- make audit reasoning traceable
- ensure consistent control coverage
- separate applicability from assessment
- separate missing controls from missing evidence
- strengthen confidence scoring
- improve regulator readiness and reviewer trust

## Position in Pipeline

1. interactive intake
2. audit planning layer
3. retrieval
4. control evaluation
5. enterprise output schema population
6. Claude report transformation
7. human review

## Audit Plan Object

The audit plan should include:

- audit_type
- entity_name
- entity_type
- industry
- jurisdictions
- applicable_regimes
- required_control_ids
- required_evidence_types
- review_focus
- decision_sensitivity

## Behavior

Given the intake object, the planning layer should deterministically select:

- which regimes are in scope
- which control families are required
- which evidence families are expected
- which retrieval terms should be emphasized

## Initial Regime Coverage

MVP jurisdictions:
- US
- UK
- EU

MVP audit types:
- AML readiness review
- KYC/KYB policy and control review
- sanctions readiness review
- policy/governance gap analysis
- vendor/internal compliance readiness review
- audit report generation from uploaded evidence

## Output Use

The audit plan drives:

- retrieval query construction
- control evaluation ordering
- completeness checks
- output confidence assessment
- reviewer traceability
