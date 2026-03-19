import json
from pathlib import Path

CASES = {
    "fraud_us_monitoring_partial": {
        "audit_id": "fraud-us-monitoring-partial-001",
        "entity_name": "Real Fraud US Monitoring Partial Case",
        "audit_type": "fraud_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_type": "payments_platform",
        "products": ["wallet", "merchant_acquiring"],
        "customer_types": ["consumer", "smb"],
        "domains": ["fraud", "governance"],
        "source_families": ["regulations", "aml", "governance", "industry_fintech"],
        "query_terms": [
            "fraud policy",
            "fraud monitoring rules",
            "fraud case management",
            "fraud governance"
        ],
        "top_k": 5
    },
    "fraud_uk_case_management_gap": {
        "audit_id": "fraud-uk-case-management-gap-001",
        "entity_name": "Real Fraud UK Case Management Gap",
        "audit_type": "fraud_readiness_review",
        "industry": "payments",
        "jurisdictions": ["UK"],
        "entity_type": "payments_platform",
        "products": ["api"],
        "customer_types": ["enterprise"],
        "domains": ["fraud", "governance"],
        "source_families": ["regulations", "governance", "industry_fintech"],
        "query_terms": [
            "fraud case management",
            "fraud escalation",
            "fraud governance"
        ],
        "top_k": 5
    },
    "screening_us_transaction_partial": {
        "audit_id": "screening-us-transaction-partial-001",
        "entity_name": "Real US Transaction Screening Partial Case",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["US"],
        "entity_type": "payments_platform",
        "products": ["cross_border_payments"],
        "customer_types": ["enterprise"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "transaction screening",
            "screening thresholds",
            "screening alert workflow"
        ],
        "top_k": 5
    },
    "screening_eu_quality_checks_gap": {
        "audit_id": "screening-eu-quality-checks-gap-001",
        "entity_name": "Real EU Screening Quality Gap",
        "audit_type": "transaction_screening_review",
        "industry": "crypto",
        "jurisdictions": ["EU"],
        "entity_type": "wallet_provider",
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "screening quality checks",
            "screening governance",
            "transaction screening"
        ],
        "top_k": 5
    },
    "licensing_uae_vendor_readiness": {
        "audit_id": "licensing-uae-vendor-readiness-001",
        "entity_name": "Real UAE Licensing Vendor Readiness",
        "audit_type": "regulatory_licensing_readiness_review",
        "industry": "payments",
        "jurisdictions": ["UAE"],
        "entity_type": "vendor",
        "products": ["api"],
        "customer_types": ["enterprise"],
        "domains": ["regulatory_licensing", "vendor_risk", "governance"],
        "source_families": ["regulations", "vendor_risk", "governance", "industry_fintech"],
        "query_terms": [
            "licensing inventory",
            "regulatory mapping",
            "vendor due diligence procedure",
            "licensing governance"
        ],
        "top_k": 5
    },
    "licensing_singapore_governance_partial": {
        "audit_id": "licensing-singapore-governance-partial-001",
        "entity_name": "Real Singapore Licensing Governance Partial",
        "audit_type": "regulatory_licensing_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["SINGAPORE"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "domains": ["regulatory_licensing", "governance"],
        "source_families": ["regulations", "governance", "industry_fintech"],
        "query_terms": [
            "licensing obligations",
            "regulatory accountability",
            "licensing governance"
        ],
        "top_k": 5
    },
    "remediation_us_issue_tracker_gap": {
        "audit_id": "remediation-us-issue-tracker-gap-001",
        "entity_name": "Real US Remediation Issue Tracker Gap",
        "audit_type": "remediation_tracking_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "smb"],
        "domains": ["remediation_tracking", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "issue register",
            "action tracker",
            "owner assignment",
            "remediation governance"
        ],
        "top_k": 5
    },
    "remediation_canada_closure_partial": {
        "audit_id": "remediation-canada-closure-partial-001",
        "entity_name": "Real Canada Remediation Closure Partial",
        "audit_type": "remediation_tracking_review",
        "industry": "payments",
        "jurisdictions": ["CANADA"],
        "entity_type": "payments_platform",
        "products": ["api"],
        "customer_types": ["enterprise"],
        "domains": ["remediation_tracking", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "closure evidence",
            "issue register",
            "remediation governance"
        ],
        "top_k": 5
    },
    "screening_hk_false_positive_review": {
        "audit_id": "screening-hk-false-positive-review-001",
        "entity_name": "Real Hong Kong False Positive Review",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["HONG_KONG"],
        "entity_type": "payments_platform",
        "products": ["cross_border_payments"],
        "customer_types": ["enterprise"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "false positive review",
            "screening alert workflow",
            "screening governance"
        ],
        "top_k": 5
    },
    "fraud_australia_governance_heavy": {
        "audit_id": "fraud-australia-governance-heavy-001",
        "entity_name": "Real Australia Fraud Governance Heavy",
        "audit_type": "fraud_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["AUSTRALIA"],
        "entity_type": "payments_platform",
        "products": ["wallet", "api"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["fraud", "governance", "remediation_tracking"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "fraud governance",
            "fraud escalation",
            "issue register",
            "roles and responsibilities"
        ],
        "top_k": 5
    }
}

root = Path("evals/gold_cases")
root.mkdir(parents=True, exist_ok=True)

for case_id, ctx in CASES.items():
    case_dir = root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "audit_context.json").write_text(json.dumps(ctx, indent=2), encoding="utf-8")
    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": case_id,
        "expected": {
            "equals": {},
            "contains": {},
            "minimums": {}
        }
    }, indent=2), encoding="utf-8")
    (case_dir / "case_notes.md").write_text(
        f"# {case_id}\n\n## Scenario\nReal corpus-backed future-pack case.\n\n## Human adjudication\nTo be completed after deterministic run review.\n\n## Reviewer rationale\nComplete after reviewing initial_run_output.json.\n",
        encoding="utf-8"
    )
    print("seeded", case_id)
