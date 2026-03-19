# Tenet System Architecture

## North Star

Tenet is an end-to-end global compliance intelligence platform.

The system performs deep structured compliance reasoning across domains and jurisdictions, then transforms structured audit outputs into premium enterprise reports.

## Delivery Flow

1. interactive intake
2. audit planning
3. retrieval
4. control evaluation
5. structured audit JSON
6. report transformation layer
7. human review
8. final enterprise delivery

## MVP Principle

Current MVP:
- RAG + frontier model + human review
- no fine-tuning yet
- reasoning brain first
- UI later

## MVP Jurisdictions

- US
- UK
- EU

## MVP Industries

- fintech
- payments
- crypto

## MVP Audit Types

- AML readiness review
- KYC/KYB policy and control review
- sanctions readiness review
- policy/governance gap analysis
- vendor/internal compliance readiness review
- audit report generation from uploaded evidence

## Core Rule

Tenet must not jump directly from retrieval to final findings.

It must reason through:
- applicability
- expected controls
- evidence sufficiency
- control status
- findings
- risk
- remediation
- decision

## Current Build Priority

Reasoning quality and audit structure before UI sophistication.
