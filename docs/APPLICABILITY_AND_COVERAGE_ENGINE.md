# Applicability and Coverage Engine

## Purpose

This layer sits between retrieval and final audit JSON generation.

It converts an audit context into:
1. applicable control obligations
2. evidence coverage assessment
3. deterministic missing controls / missing evidence outputs

This is the core step that upgrades Tenet from retrieval-driven summarization to structured compliance reasoning.

## Position in pipeline

1. interactive intake
2. retrieval query construction
3. retrieval
4. applicability engine
5. coverage engine
6. finding synthesis
7. enterprise output JSON
8. Claude report transformation
9. human review

## Why this layer matters

Regulator-ready outputs require:
- explicit scope logic
- explicit control expectations
- explicit evidence support
- explainable gaps
- reproducible decisions

Without this layer, findings risk being too prompt-shaped and insufficiently auditable.

## MVP design

For MVP, this layer is deterministic and rule-backed.

Inputs:
- audit_id
- industry
- jurisdictions
- audit_type
- source_families
- query_terms
- top_k

Optional inputs:
- entity_type
- products
- delivery_channels
- evidence_documents
- reviewer_notes

Outputs:
- applicable obligations
- coverage matrix
- supported controls
- partial controls
- missing controls
- missing evidence
- evidence-backed findings
- confidence inputs

## Applicability engine

The applicability engine determines which controls must be assessed for a given audit context.

For MVP, obligations are determined using:
- audit_type
- industry
- jurisdictions
- source_families

Each obligation should include:
- obligation_id
- regime_slug
- control_id
- control_name
- audit_domains
- jurisdictions
- industries
- rationale
- severity
- evidence_expectations

## Coverage engine

The coverage engine evaluates retrieved chunks against applicable obligations.

Coverage states:
- supported
- partial
- missing

Coverage should be based on:
- chunk metadata alignment
- keyword anchors
- evidence density
- citation quality

## Enterprise output impact

The following output schema sections should be driven primarily by the applicability and coverage layer:
- regulatory_applicability
- control_assessment
- findings
- key_risks
- missing_controls
- missing_evidence
- remediation_roadmap
- confidence_assessment

## MVP principle

This layer must be:
- deterministic first
- explainable
- citation-backed
- safe for human review
- easy to expand later into deeper regime-specific reasoning
