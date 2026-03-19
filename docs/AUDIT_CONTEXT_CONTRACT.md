# Audit Context Contract

## Required Fields
- audit_type
- industry
- jurisdictions

## Optional Fields
- entity_name
- entity_type
- products
- customer_types
- delivery_channels
- evidence_paths
- notes

## Example
{
  "audit_type": "aml_readiness_review",
  "industry": "fintech",
  "jurisdictions": ["US", "UK"],
  "entity_name": "ExampleCo",
  "entity_type": "payments_platform",
  "products": ["wallet", "card_issuing"],
  "customer_types": ["consumer", "smb"],
  "evidence_paths": [],
  "notes": "Initial AML readiness assessment"
}
