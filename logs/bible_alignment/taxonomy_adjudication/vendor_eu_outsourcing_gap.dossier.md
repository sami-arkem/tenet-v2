# Taxonomy Adjudication Dossier: vendor_eu_outsourcing_gap

- case_dir: `evals/gold_cases/vendor_eu_outsourcing_gap`
- issues: `['domains must be a non-empty list']`

## Folder Name Hints

- domains: `['vendor_risk']`
- jurisdictions: `['eu']`

## Current Audit Context

```json
{
  "audit_id": "vendor-eu-outsourcing-gap-001",
  "entity_name": "Real Vendor EU Outsourcing Gap Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "payments",
  "jurisdictions": [
    "EU"
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
    "vendor due diligence procedure",
    "outsourcing governance",
    "third party risk assessment",
    "vendor monitoring cadence",
    "approval workflow"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

## Recovery Context

```json
{
  "case_dir": "evals/gold_cases/vendor_eu_outsourcing_gap",
  "changed": false,
  "blocked": true,
  "domain_before": null,
  "jurisdiction_before": [
    "EU"
  ],
  "domain_after": null,
  "jurisdiction_after": [
    "EU"
  ],
  "reasons": [
    "domain: ambiguous top candidates at same confidence: ['governance', 'vendor_risk']"
  ],
  "backup_dir": null
}
```

## Evidence Snippets

### evals/gold_cases/vendor_eu_outsourcing_gap/audit_context.json

```text
{
  "audit_id": "vendor-eu-outsourcing-gap-001",
  "entity_name": "Real Vendor EU Outsourcing Gap Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "payments",
  "jurisdictions": [
    "EU"
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
    "vendor due diligence procedure",
    "outsourcing governance",
    "third party risk assessment",
    "vendor monitoring cadence",
    "approval workflow"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

### evals/gold_cases/vendor_eu_outsourcing_gap/case_notes.md

```text
# vendor_eu_outsourcing_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: vendor_internal_compliance_readiness_review
- industry: payments
- jurisdictions: EU
- entity_name: Real Vendor EU Outsourcing Gap Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- THIRD_PARTY_RISK
- GOVERNANCE_BASELINE

## Expected control position
- missing_controls: GOV-001, VEN-001
- missing_evidence: GOV-001, VEN-001
- findings: VEN-001, GOV-001
- control_coverage_score minimum: 18

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
```

### evals/gold_cases/vendor_eu_outsourcing_gap/expected_assertions.json

```text
{
  "case_id": "vendor_eu_outsourcing_gap",
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
        "VEN-001",
        "GOV-001"
      ]
    },
    "minimums": {
      "control_assessment.control_coverage_score": 18
    }
  },
  "rules": {
    "no_invented_pass_outcome": true,
    "deterministic_current_truth_only": true,
    "historical_context_cannot_override_current_truth": true
  }
}
```

### evals/gold_cases/vendor_eu_outsourcing_gap/initial_run_output.json

```text
{
  "audit_meta": {
    "audit_id": "vendor-eu-outsourcing-gap-001",
    "audit_version": "v1",
    "timestamp_utc": "2026-03-17T15:09:12.144439+00:00",
    "platform_version": "tenet-mvp",
    "model_version": "deterministic-reasoner-v1",
    "report_status": "draft",
    "reasoning_mode": "deterministic"
  },
  "entity_profile": {
    "legal_name": "Real Vendor EU Outsourcing Gap Case",
    "trade_name": "",
    "industry": "payments",
    "subindustry": "",
    "business_model": "",
    "products_services": [
      "api"
    ],
    "jurisdictions_of_operation": [
      "EU"
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
    "scope_statement": "vendor_internal_compliance_readiness_review for payments across EU",
    "included_domains": [
      "governance",
      "vendor_risk"
    ],
    "excluded_domains": [],
    "documents_reviewed": [
      "EBA AML CFT",
      "NYDFS Cybersecurity",
      "UK MLR 2017"
    ],
    "evidence
```

## Required Decision JSON Shape

```json
{
  "case_dir": "evals/gold_cases/vendor_eu_outsourcing_gap",
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
