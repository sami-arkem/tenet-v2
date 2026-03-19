# Reasoning Input Object

The reasoning layer should accept structured audit context sufficient to produce an audit plan.

## Recommended Fields

- audit_type
- entity_name
- entity_type
- industry
- jurisdictions
- products
- customer_types
- evidence_paths
- optional business model notes

## Minimum Required for Audit Planning

- audit_type
- industry
- jurisdictions

## Planning Output

The planning layer should derive:

- applicable_regimes
- required_control_ids
- required_evidence_types
- review_focus
- decision_sensitivity
