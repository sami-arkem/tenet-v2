# Taxonomy Adjudication Dossier: kyc_us_consumer_onboarding_gap

- case_dir: `evals/gold_cases/kyc_us_consumer_onboarding_gap`
- issues: `['domains must be a non-empty list']`

## Folder Name Hints

- domains: `['kyc']`
- jurisdictions: `['us']`

## Current Audit Context

```json
{
  "audit_id": "kyc-us-consumer-onboarding-gap-001",
  "entity_name": "Real KYC US Consumer Gap Case",
  "audit_type": "kyc_kyb_policy_and_control_review",
  "industry": "fintech",
  "jurisdictions": [
    "US"
  ],
  "entity_type": "wallet_provider",
  "products": [
    "wallet"
  ],
  "customer_types": [
    "consumer"
  ],
  "source_families": [
    "regulations",
    "aml",
    "kyc",
    "industry_fintech"
  ],
  "query_terms": [
    "cip policy",
    "identity verification workflow",
    "consumer onboarding",
    "customer risk scoring",
    "onboarding procedure"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

## Recovery Context

```json
{
  "case_dir": "evals/gold_cases/kyc_us_consumer_onboarding_gap",
  "changed": false,
  "blocked": true,
  "domain_before": null,
  "jurisdiction_before": [
    "US"
  ],
  "domain_after": null,
  "jurisdiction_after": [
    "US"
  ],
  "reasons": [
    "domain: ambiguous top candidates at same confidence: ['aml', 'kyc']"
  ],
  "backup_dir": null
}
```

## Evidence Snippets

### evals/gold_cases/kyc_us_consumer_onboarding_gap/audit_context.json

```text
{
  "audit_id": "kyc-us-consumer-onboarding-gap-001",
  "entity_name": "Real KYC US Consumer Gap Case",
  "audit_type": "kyc_kyb_policy_and_control_review",
  "industry": "fintech",
  "jurisdictions": [
    "US"
  ],
  "entity_type": "wallet_provider",
  "products": [
    "wallet"
  ],
  "customer_types": [
    "consumer"
  ],
  "source_families": [
    "regulations",
    "aml",
    "kyc",
    "industry_fintech"
  ],
  "query_terms": [
    "cip policy",
    "identity verification workflow",
    "consumer onboarding",
    "customer risk scoring",
    "onboarding procedure"
  ],
  "top_k": 5,
  "historical_context_is_non_authoritative": true,
  "deterministic_current_audit_truth_only": true
}
```

### evals/gold_cases/kyc_us_consumer_onboarding_gap/case_notes.md

```text
# kyc_us_consumer_onboarding_gap

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: kyc_kyb_policy_and_control_review
- industry: fintech
- jurisdictions: US
- entity_name: Real KYC US Consumer Gap Case

## Human adjudication
Expected outcome is BLOCKED based on the current corpus-backed deterministic output.

## Expected regimes
- CIP_KYC
- CDD_BO

## Expected control position
- missing_controls: AML-002, GOV-001, KYB-001, KYC-001
- missing_evidence: AML-002, GOV-001, KYB-001, KYC-001
- findings: KYB-001, KYC-001, AML-002, GOV-001
- control_coverage_score minimum: 0

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
```

### evals/gold_cases/kyc_us_consumer_onboarding_gap/expected_assertions.json

```text
{
  "case_id": "kyc_us_consumer_onboarding_gap",
  "expected": {
    "equals": {
      "deployment_decision.status": "BLOCKED"
    },
    "contains": {
      "regulatory_applicability.primary_regimes": [
        "CIP_KYC",
        "CDD_BO"
      ],
      "missing_controls.control_id": [
        "AML-002",
        "GOV-001",
        "KYB-001",
        "KYC-001"
      ],
      "missing_evidence.control_id": [
        "AML-002",
        "GOV-001",
        "KYB-001",
        "KYC-001"
      ],
      "findings.control_id": [
        "KYB-001",
        "KYC-001",
        "AML-002",
        "GOV-001"
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

### evals/gold_cases/kyc_us_consumer_onboarding_gap/initial_run_output.json

```text
{
  "audit_meta": {
    "audit_id": "kyc-us-consumer-onboarding-gap-001",
    "audit_version": "v1",
    "timestamp_utc": "2026-03-17T15:09:11.684713+00:00",
    "platform_version": "tenet-mvp",
    "model_version": "deterministic-reasoner-v1",
    "report_status": "draft",
    "reasoning_mode": "deterministic"
  },
  "entity_profile": {
    "legal_name": "Real KYC US Consumer Gap Case",
    "trade_name": "",
    "industry": "fintech",
    "subindustry": "",
    "business_model": "",
    "products_services": [
      "wallet"
    ],
    "jurisdictions_of_operation": [
      "US"
    ],
    "customer_geographies": [],
    "customer_types": [
      "consumer"
    ],
    "distribution_channels": [],
    "payment_flows": [],
    "data_categories_processed": [],
    "high_risk_activities": []
  },
  "audit_scope": {
    "audit_type": "kyc_kyb_policy_and_control_review",
    "scope_statement": "kyc_kyb_policy_and_control_review for fintech across US",
    "included_domains": [
      "aml_governance",
      "customer_identification",
      "governance",
      "kyb_beneficial_ownership",
      "kyc_kyb"
    ],
    "excluded_domains": [],
    "documents_reviewed": [
      "AML CTF Act",
    
```

## Required Decision JSON Shape

```json
{
  "case_dir": "evals/gold_cases/kyc_us_consumer_onboarding_gap",
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
