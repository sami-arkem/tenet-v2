# Tenet Retrieval Query Object

The reasoning layer should not send raw user text directly to retrieval.

It should first normalize intake into a query object:

- industry
- jurisdictions
- audit_type
- source_families
- query_terms
- excluded_families
- top_k

## Example
{
  "industry": "fintech",
  "jurisdictions": ["us", "uk", "eu"],
  "audit_type": "aml_readiness_review",
  "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
  "query_terms": [
    "aml",
    "kyc",
    "sanctions",
    "customer due diligence",
    "controls",
    "governance"
  ],
  "top_k": 12
}
