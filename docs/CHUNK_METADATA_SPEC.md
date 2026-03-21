# Tenet Chunk Metadata Spec

Every retrieval chunk must contain:

- source_family
- source_name
- document_name
- url
- jurisdiction
- industry
- audit_domain
- quality_status
- chunk_id
- text

## Rules
1. No chunk without source_family.
2. No chunk without source_name.
3. No chunk without document_name.
4. No chunk without chunk_id.
5. Every chunk must be traceable back to one source document.
6. Retrieval must be able to filter by:
   - jurisdiction
   - industry
   - source_family
   - audit_domain
