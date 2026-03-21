# Tenet RAG Architecture

## Goal
Turn the compliance corpus into a retrieval-ready intelligence layer for Tenet.

## Pipeline
1. clean source documents
2. normalize metadata
3. chunk documents
4. attach metadata to every chunk
5. index chunks for retrieval
6. retrieve by audit context
7. feed retrieved context into reasoning layer
8. output structured audit JSON
9. send structured JSON to Claude for premium report generation

## Required Metadata Per Chunk
- source_family
- source_name
- document_name
- url
- jurisdiction
- industry
- audit_domain
- quality_status
- chunk_id

## Initial Retrieval Strategy
- hybrid retrieval
- metadata filtering
- source-family aware ranking
- jurisdiction-aware ranking
- industry-aware ranking

## MVP Retrieval Families
- regulations
- aml
- enforcement
- frameworks
- corporate
- licensing
- industry_fintech
- industry_payments
- industry_crypto

## Output Requirement
Retrieval must return:
- chunk text
- metadata
- traceable source identity
