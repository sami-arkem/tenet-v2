# Intake Contract

Tenet intake accepts natural language, uploaded evidence references, and structured answers.

The intake layer must convert all user input into a canonical machine-readable audit context.

## Required canonical fields

- audit_type
- industry
- jurisdictions

## Core optional fields

- entity_name
- entity_type
- trade_name
- business_model
- products
- customer_types
- customer_geographies
- distribution_channels
- payment_flows
- data_categories_processed
- high_risk_activities
- source_families
- query_terms
- evidence_paths
- excluded_domains
- notes

## Intake design rules

- user may answer in messy natural language
- intake must normalize to canonical enums
- intake must track confidence and uncertainty
- intake must not ask repetitive or low-value questions
- intake must explain why a question matters when useful
- intake should feel conversational, sharp, calm, and premium
- light humor is allowed, but never at the expense of clarity or trust

## Output contract

The final intake output must be a valid reasoning input object consumable by Tenet reasoning.

## Example canonical object

{
  "audit_type": "aml_readiness_review",
  "industry": "fintech",
  "jurisdictions": ["US", "UK"],
  "entity_name": "ExampleCo",
  "entity_type": "payments_platform",
  "business_model": "B2B payments infrastructure",
  "products": ["wallet", "card_issuing"],
  "customer_types": ["smb", "consumer"],
  "customer_geographies": ["US", "UK"],
  "distribution_channels": ["api", "dashboard"],
  "payment_flows": ["wallet_funding", "merchant_settlement"],
  "data_categories_processed": ["identity_data", "transaction_data"],
  "high_risk_activities": ["cross_border_payments"],
  "source_families": ["regulations", "aml", "industry_fintech"],
  "query_terms": ["aml", "kyc", "kyb", "sanctions", "transaction monitoring"],
  "evidence_paths": [],
  "excluded_domains": [],
  "notes": "Initial intake completed"
}
