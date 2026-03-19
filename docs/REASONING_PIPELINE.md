# Reasoning Pipeline

## Current Target Architecture

1. interactive intake
2. audit planning layer
3. retrieval query generation
4. retrieval
5. control evaluation
6. structured audit JSON generation
7. Claude report transformation layer
8. human review
9. final enterprise-ready delivery

## Why This Structure

The reasoning system should not move directly from retrieved chunks to findings.

It should first determine:

- what audit is being performed
- what regimes apply
- what controls are expected
- what evidence should exist

Only after that should it generate:

- control assessment
- findings
- key risks
- missing controls
- missing evidence
- remediation roadmap
- deployment decision
- confidence assessment

## New Components

### Audit Planning Layer
Builds a deterministic audit plan from intake context.

### Control Evaluation Layer
Assesses each required control against retrieved evidence and records citations, rationale, status, and confidence.

## Output Consequences

This structure strengthens:
- regulator traceability
- consistency across audits
- reviewer usability
- report quality
