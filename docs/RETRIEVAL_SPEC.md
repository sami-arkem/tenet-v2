# Tenet Retrieval Spec

## Goal
Given structured audit context, retrieve the most relevant compliance chunks for reasoning.

## Retrieval Inputs
- industry
- jurisdictions
- audit_type
- source_families
- query_terms
- optional document filters

## Retrieval Outputs
A ranked list of chunks with:
- text
- source_family
- source_name
- document_name
- url
- jurisdiction
- industry
- audit_domain
- quality_status
- score

## MVP Retrieval Rules
1. Retrieval must prefer:
   - matching jurisdiction
   - matching industry
   - matching source_family
2. Retrieval must support hybrid ranking:
   - keyword overlap
   - metadata match
3. Retrieval must return traceable chunks only.
4. Retrieval must over-retrieve first, then rerank.
5. Retrieval should be deterministic enough for evaluation.

## MVP Priority Families
- regulations
- aml
- enforcement
- frameworks
- corporate
- licensing
- industry_fintech
- industry_payments
- industry_crypto
