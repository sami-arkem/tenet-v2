# Evidence Pack Spec

## Purpose
A customer evidence pack is the real unit of work Tenet should operate on.

## Minimum required file
- audit_context.json

## audit_context.json required fields
- audit_id
- entity_name
- audit_type
- industry
- jurisdictions
- source_families
- query_terms
- top_k

## Optional high-value fields
- domains
- entity_type
- products
- customer_types
- notes
- reasoning_model_name

## Example usage
A real customer pack should map to one enterprise review:
- AML readiness
- KYC/KYB control review
- sanctions readiness
- governance gap analysis
- vendor/internal readiness
- future fraud/screening/licensing/remediation reviews
