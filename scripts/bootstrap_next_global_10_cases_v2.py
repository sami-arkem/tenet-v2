import json
from pathlib import Path

CASES = {
    "uae_transaction_screening_escalation_gap": {
        "audit_id": "uae-transaction-screening-escalation-gap-001",
        "entity_name": "Real UAE Transaction Screening Escalation Gap",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["UAE"],
        "entity_type": "payments_platform",
        "products": ["cross_border_payments", "wallet"],
        "customer_types": ["enterprise", "consumer"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "governance", "industry_fintech"],
        "query_terms": [
            "transaction screening",
            "screening alert workflow",
            "screening escalation",
            "screening governance",
            "screening quality checks"
        ],
        "top_k": 5
    },
    "singapore_fraud_monitoring_governance_partial": {
        "audit_id": "singapore-fraud-monitoring-governance-partial-001",
        "entity_name": "Real Singapore Fraud Monitoring Governance Partial",
        "audit_type": "fraud_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["SINGAPORE"],
        "entity_type": "wallet_provider",
        "products": ["wallet", "api"],
        "customer_types": ["consumer", "smb"],
        "domains": ["fraud", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "fraud policy",
            "fraud monitoring rules",
            "fraud governance",
            "fraud escalation",
            "case management"
        ],
        "top_k": 5
    },
    "hong_kong_transaction_screening_false_positive_partial": {
        "audit_id": "hong-kong-transaction-screening-false-positive-partial-001",
        "entity_name": "Real Hong Kong Transaction Screening False Positive Partial",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["HONG_KONG"],
        "entity_type": "payments_platform",
        "products": ["api", "cross_border_payments"],
        "customer_types": ["enterprise"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "false positive review",
            "screening alert workflow",
            "transaction screening",
            "screening governance",
            "alert disposition"
        ],
        "top_k": 5
    },
    "canada_remediation_issue_register_gap": {
        "audit_id": "canada-remediation-issue-register-gap-001",
        "entity_name": "Real Canada Remediation Issue Register Gap",
        "audit_type": "remediation_tracking_review",
        "industry": "payments",
        "jurisdictions": ["CANADA"],
        "entity_type": "payments_platform",
        "products": ["api"],
        "customer_types": ["enterprise"],
        "domains": ["remediation_tracking", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "issue register",
            "action tracker",
            "owner assignment",
            "closure evidence",
            "remediation governance"
        ],
        "top_k": 5
    },
    "australia_regulatory_licensing_vendor_governance_gap": {
        "audit_id": "australia-regulatory-licensing-vendor-governance-gap-001",
        "entity_name": "Real Australia Regulatory Licensing Vendor Governance Gap",
        "audit_type": "regulatory_licensing_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["AUSTRALIA"],
        "entity_type": "vendor",
        "products": ["api", "dashboard"],
        "customer_types": ["enterprise"],
        "domains": ["regulatory_licensing", "vendor_risk", "governance"],
        "source_families": ["vendor_risk", "governance", "industry_fintech"],
        "query_terms": [
            "licensing inventory",
            "regulatory mapping",
            "licensing governance",
            "vendor due diligence procedure",
            "outsourcing governance"
        ],
        "top_k": 5
    },
    "uae_regulatory_licensing_accountability_partial": {
        "audit_id": "uae-regulatory-licensing-accountability-partial-001",
        "entity_name": "Real UAE Regulatory Licensing Accountability Partial",
        "audit_type": "regulatory_licensing_readiness_review",
        "industry": "payments",
        "jurisdictions": ["UAE"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "smb"],
        "domains": ["regulatory_licensing", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "licensing obligations",
            "regulatory accountability",
            "ownership and accountability",
            "licensing governance",
            "roles and responsibilities"
        ],
        "top_k": 5
    },
    "singapore_remediation_closure_evidence_partial": {
        "audit_id": "singapore-remediation-closure-evidence-partial-001",
        "entity_name": "Real Singapore Remediation Closure Evidence Partial",
        "audit_type": "remediation_tracking_review",
        "industry": "fintech",
        "jurisdictions": ["SINGAPORE"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["remediation_tracking", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "closure evidence",
            "issue register",
            "action tracker",
            "remediation governance",
            "owner assignment"
        ],
        "top_k": 5
    },
    "hong_kong_fraud_case_management_gap": {
        "audit_id": "hong-kong-fraud-case-management-gap-001",
        "entity_name": "Real Hong Kong Fraud Case Management Gap",
        "audit_type": "fraud_readiness_review",
        "industry": "payments",
        "jurisdictions": ["HONG_KONG"],
        "entity_type": "payments_platform",
        "products": ["wallet", "api"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["fraud", "governance", "remediation_tracking"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "fraud case management",
            "fraud policy",
            "fraud escalation",
            "issue register",
            "fraud governance"
        ],
        "top_k": 5
    },
    "canada_transaction_screening_governance_partial": {
        "audit_id": "canada-transaction-screening-governance-partial-001",
        "entity_name": "Real Canada Transaction Screening Governance Partial",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["CANADA"],
        "entity_type": "payments_platform",
        "products": ["cross_border_payments"],
        "customer_types": ["enterprise"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "governance", "industry_fintech"],
        "query_terms": [
            "transaction screening",
            "screening governance",
            "screening quality checks",
            "screening escalation",
            "alert workflow"
        ],
        "top_k": 5
    },
    "australia_fraud_remediation_heavy": {
        "audit_id": "australia-fraud-remediation-heavy-001",
        "entity_name": "Real Australia Fraud Remediation Heavy",
        "audit_type": "fraud_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["AUSTRALIA"],
        "entity_type": "payments_platform",
        "products": ["wallet", "merchant_acquiring"],
        "customer_types": ["consumer", "smb"],
        "domains": ["fraud", "governance", "remediation_tracking"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "fraud monitoring rules",
            "issue register",
            "action tracker",
            "fraud governance",
            "closure evidence"
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
        f"# {case_id}\n\n## Scenario\nReal corpus-backed global expansion case.\n\n## Human adjudication\nTo be completed after deterministic run review.\n\n## Reviewer rationale\nComplete after reviewing initial_run_output.json.\n",
        encoding="utf-8"
    )
    print("seeded", case_id)
