# Taxonomy Adjudication Dossier: vendor_readiness_us_uk

- case_dir: `evals/gold_cases/vendor_readiness_us_uk`
- issues: `['domains must be a non-empty list']`

## Folder Name Hints

- domains: `['vendor_risk']`
- jurisdictions: `['uk', 'us']`

## Current Audit Context

```json
{
  "audit_id": "vendor-readiness-us-uk-001",
  "entity_name": "Real Vendor Readiness Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "payments",
  "jurisdictions": [
    "US",
    "UK"
  ],
  "entity_type": "vendor",
  "products": [
    "api"
  ],
  "customer_types": [
    "enterprise"
  ],
  "source_families": [
    "regulations",
    "vendor_risk",
    "governance",
    "industry_fintech"
  ],
  "query_terms": [
    "vendor due diligence",
    "third party risk",
    "vendor monitoring",
    "outsourcing governance",
    "compliance oversight"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

## Recovery Context

```json
{
  "case_dir": "evals/gold_cases/vendor_readiness_us_uk",
  "changed": false,
  "blocked": true,
  "domain_before": null,
  "jurisdiction_before": [
    "US",
    "UK"
  ],
  "domain_after": null,
  "jurisdiction_after": [
    "US",
    "UK"
  ],
  "reasons": [
    "domain: ambiguous top candidates at same confidence: ['governance', 'vendor_risk']"
  ],
  "backup_dir": null
}
```

## Evidence Snippets

### evals/gold_cases/vendor_readiness_us_uk/audit_context.json

```text
{
  "audit_id": "vendor-readiness-us-uk-001",
  "entity_name": "Real Vendor Readiness Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "payments",
  "jurisdictions": [
    "US",
    "UK"
  ],
  "entity_type": "vendor",
  "products": [
    "api"
  ],
  "customer_types": [
    "enterprise"
  ],
  "source_families": [
    "regulations",
    "vendor_risk",
    "governance",
    "industry_fintech"
  ],
  "query_terms": [
    "vendor due diligence",
    "third party risk",
    "vendor monitoring",
    "outsourcing governance",
    "compliance oversight"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

### evals/gold_cases/vendor_readiness_us_uk/case_notes.md

```text
# vendor_readiness_us_uk

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: vendor_internal_compliance_readiness_review
- industry: payments
- jurisdictions: US, UK
- entity_name: Real Vendor Readiness Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- THIRD_PARTY_RISK
- GOVERNANCE_BASELINE

## Expected control position
- missing_controls: GOV-001, VEN-001
- missing_evidence: GOV-001, VEN-001
- findings: GOV-001, VEN-001
- control_coverage_score minimum: 0

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
```

### evals/gold_cases/vendor_readiness_us_uk/expected_assertions.json

```text
{
  "case_id": "vendor_readiness_us_uk",
  "expected": {
    "equals": {
      "deployment_decision.status": "BLOCKED"
    },
    "contains": {
      "regulatory_applicability.primary_regimes": [
        "THIRD_PARTY_RISK",
        "GOVERNANCE_BASELINE"
      ],
      "missing_controls.control_id": [
        "GOV-001",
        "VEN-001"
      ],
      "missing_evidence.control_id": [
        "GOV-001",
        "VEN-001"
      ],
      "findings.control_id": [
        "GOV-001",
        "VEN-001"
      ]
    },
    "minimums": {
      "control_assessment.control_coverage_score": 0
    }
  },
  "rules": {
    "no_invented_pass_outcome": true,
    "deterministic_current_truth_only": true,
    "historical_context_cannot_override_current_truth": true
  }
}
```

### evals/gold_cases/vendor_readiness_us_uk/initial_run_output.json

```text
{
  "audit_meta": {
    "audit_id": "vendor-readiness-us-uk-001",
    "audit_version": "v1",
    "timestamp_utc": "2026-03-17T15:09:12.220447+00:00",
    "platform_version": "tenet-mvp",
    "model_version": "deterministic-reasoner-v1",
    "report_status": "draft",
    "reasoning_mode": "deterministic"
  },
  "entity_profile": {
    "legal_name": "Real Vendor Readiness Case",
    "trade_name": "",
    "industry": "payments",
    "subindustry": "",
    "business_model": "",
    "products_services": [
      "api"
    ],
    "jurisdictions_of_operation": [
      "US",
      "UK"
    ],
    "customer_geographies": [],
    "customer_types": [
      "enterprise"
    ],
    "distribution_channels": [],
    "payment_flows": [],
    "data_categories_processed": [],
    "high_risk_activities": []
  },
  "audit_scope": {
    "audit_type": "vendor_internal_compliance_readiness_review",
    "scope_statement": "vendor_internal_compliance_readiness_review for payments across US, UK",
    "included_domains": [
      "governance",
      "vendor_risk"
    ],
    "excluded_domains": [],
    "documents_reviewed": [
      "FCA Money Laundering Regulations",
      "NYDFS Cybersecurity",
      "UK MLR 2
```

## Required Decision JSON Shape

```json
{
  "case_dir": "evals/gold_cases/vendor_readiness_us_uk",
  "domains": [
    "..."
  ],
  "jurisdictions": [
    "..."
  ],
  "decided_by": "...",
  "rationale": "...",
  "evidence_refs": [
    "path/to/file",
    "other/file#section"
  ]
}
```
