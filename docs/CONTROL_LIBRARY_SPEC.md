# Control Library Spec

## Purpose

The control library defines the deterministic baseline of expected controls for each audit type.

The reasoning layer should evaluate evidence against this library rather than generating findings from scratch.

## Design Principles

- machine readable
- jurisdiction aware
- industry aware
- audit-type aware
- evidence aware
- severity aware

## Control Object

Each control record should contain:

- control_id
- title
- description
- domain
- audit_types
- jurisdictions
- industries
- source_regimes
- required_evidence
- expected_artifacts
- keywords
- severity_if_missing

## Status Model

Control evaluation should assign:

- met
- partial
- missing
- unknown

Evidence sufficiency should assign:

- sufficient
- partial
- missing
- not_reviewed

## Distinction

Missing control:
A required control is absent or materially inadequate.

Missing evidence:
The control may exist, but evidence provided is insufficient to verify it.

These must remain separate in output generation.

## Initial Domains

- customer risk assessment
- customer identification and verification
- beneficial ownership
- sanctions screening
- transaction monitoring
- suspicious activity escalation
- case management
- policy governance
- training and awareness
- independent review
- vendor oversight
- recordkeeping
