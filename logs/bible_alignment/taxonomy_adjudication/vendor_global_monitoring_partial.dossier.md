# Taxonomy Adjudication Dossier: vendor_global_monitoring_partial

- case_dir: `evals/gold_cases/vendor_global_monitoring_partial`
- issues: `['domains must be a non-empty list']`

## Folder Name Hints

- domains: `['vendor_risk']`
- jurisdictions: `['global']`

## Current Audit Context

```json
{
  "audit_id": "vendor-global-monitoring-partial-001",
  "entity_name": "Real Vendor Global Monitoring Partial Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "fintech",
  "jurisdictions": [
    "US",
    "UK",
    "EU"
  ],
  "entity_type": "vendor",
  "products": [
    "api",
    "dashboard"
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
    "vendor monitoring cadence",
    "third party governance",
    "outsourcing oversight",
    "risk review committee",
    "vendor escalation"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

## Recovery Context

```json
{
  "case_dir": "evals/gold_cases/vendor_global_monitoring_partial",
  "changed": false,
  "blocked": true,
  "domain_before": null,
  "jurisdiction_before": [
    "US",
    "UK",
    "EU"
  ],
  "domain_after": null,
  "jurisdiction_after": [
    "US",
    "UK",
    "EU"
  ],
  "reasons": [
    "domain: ambiguous top candidates at same confidence: ['governance', 'vendor_risk']"
  ],
  "backup_dir": null
}
```

## Evidence Snippets

### evals/gold_cases/vendor_global_monitoring_partial/audit_context.json

```text
{
  "audit_id": "vendor-global-monitoring-partial-001",
  "entity_name": "Real Vendor Global Monitoring Partial Case",
  "audit_type": "vendor_internal_compliance_readiness_review",
  "industry": "fintech",
  "jurisdictions": [
    "US",
    "UK",
    "EU"
  ],
  "entity_type": "vendor",
  "products": [
    "api",
    "dashboard"
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
    "vendor monitoring cadence",
    "third party governance",
    "outsourcing oversight",
    "risk review committee",
    "vendor escalation"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

### evals/gold_cases/vendor_global_monitoring_partial/case_notes.md

```text
# vendor_global_monitoring_partial

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: vendor_internal_compliance_readiness_review
- industry: fintech
- jurisdictions: US, UK, EU
- entity_name: Real Vendor Global Monitoring Partial Case

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

### evals/gold_cases/vendor_global_monitoring_partial/expected_assertions.json

```text
{
  "case_id": "vendor_global_monitoring_partial",
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

### evals/gold_cases/vendor_global_monitoring_partial/initial_run_output.json

```text
{
  "audit_meta": {
    "audit_id": "vendor-global-monitoring-partial-001",
    "audit_version": "v1",
    "timestamp_utc": "2026-03-17T15:09:12.182520+00:00",
    "platform_version": "tenet-mvp",
    "model_version": "deterministic-reasoner-v1",
    "report_status": "draft",
    "reasoning_mode": "deterministic"
  },
  "entity_profile": {
    "legal_name": "Real Vendor Global Monitoring Partial Case",
    "trade_name": "",
    "industry": "fintech",
    "subindustry": "",
    "business_model": "",
    "products_services": [
      "api",
      "dashboard"
    ],
    "jurisdictions_of_operation": [
      "US",
      "UK",
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
    "scope_statement": "vendor_internal_compliance_readiness_review for fintech across US, UK, EU",
    "included_domains": [
      "governance",
      "vendor_risk"
    ],
    "excluded_domains": [],
    "documents_reviewed": [
      "EBA AML CFT",
      
```

## Required Decision JSON Shape

```json
{
  "case_dir": "evals/gold_cases/vendor_global_monitoring_partial",
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
