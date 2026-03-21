import json
from pathlib import Path

CASES = {
    "aml_uae_policy_governance_gap": {
        "audit_id": "aml-uae-policy-governance-gap-001",
        "entity_name": "Real UAE AML Policy Governance Gap",
        "audit_type": "aml_readiness_review",
        "industry": "payments",
        "jurisdictions": ["UAE"],
        "entity_type": "payments_platform",
        "products": ["wallet", "cross_border_payments"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["aml", "governance"],
        "source_families": ["regulations", "aml", "governance", "industry_fintech"],
        "query_terms": [
            "aml policy",
            "policy approval",
            "aml governance",
            "roles and responsibilities",
            "transaction monitoring"
        ],
        "top_k": 5
    },
    "kyb_singapore_beneficial_ownership_gap": {
        "audit_id": "kyb-singapore-beneficial-ownership-gap-001",
        "entity_name": "Real Singapore KYB Beneficial Ownership Gap",
        "audit_type": "kyc_kyb_policy_and_control_review",
        "industry": "fintech",
        "jurisdictions": ["SINGAPORE"],
        "entity_type": "payments_platform",
        "products": ["merchant_acquiring"],
        "customer_types": ["smb"],
        "domains": ["kyc_kyb", "governance"],
        "source_families": ["regulations", "aml", "kyc", "industry_fintech"],
        "query_terms": [
            "kyb policy",
            "beneficial ownership procedure",
            "business onboarding workflow",
            "ubo verification",
            "customer risk scoring"
        ],
        "top_k": 5
    },
    "sanctions_uae_wallet_screening_partial": {
        "audit_id": "sanctions-uae-wallet-screening-partial-001",
        "entity_name": "Real UAE Wallet Screening Partial",
        "audit_type": "sanctions_readiness_review",
        "industry": "crypto",
        "jurisdictions": ["UAE"],
        "entity_type": "wallet_provider",
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "domains": ["sanctions", "transaction_screening", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "sanctions policy",
            "screening procedure",
            "transaction screening",
            "alert escalation workflow",
            "screening governance"
        ],
        "top_k": 5
    },
    "governance_canada_committee_roles_gap": {
        "audit_id": "governance-canada-committee-roles-gap-001",
        "entity_name": "Real Canada Governance Committee Roles Gap",
        "audit_type": "policy_governance_gap_analysis",
        "industry": "fintech",
        "jurisdictions": ["CANADA"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "smb"],
        "domains": ["governance", "remediation_tracking"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "governance framework",
            "committee charter",
            "roles and responsibilities",
            "escalation matrix",
            "issue register"
        ],
        "top_k": 5
    },
    "vendor_hong_kong_outsourcing_monitoring_gap": {
        "audit_id": "vendor-hong-kong-outsourcing-monitoring-gap-001",
        "entity_name": "Real Hong Kong Vendor Outsourcing Monitoring Gap",
        "audit_type": "vendor_internal_compliance_readiness_review",
        "industry": "payments",
        "jurisdictions": ["HONG_KONG"],
        "entity_type": "vendor",
        "products": ["api"],
        "customer_types": ["enterprise"],
        "domains": ["vendor_risk", "governance", "regulatory_licensing"],
        "source_families": ["vendor_risk", "governance", "industry_fintech"],
        "query_terms": [
            "vendor due diligence procedure",
            "outsourcing governance",
            "vendor monitoring cadence",
            "third party risk assessment",
            "licensing governance"
        ],
        "top_k": 5
    },
    "fraud_uae_case_management_partial": {
        "audit_id": "fraud-uae-case-management-partial-001",
        "entity_name": "Real UAE Fraud Case Management Partial",
        "audit_type": "fraud_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["UAE"],
        "entity_type": "payments_platform",
        "products": ["wallet", "api"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["fraud", "governance", "remediation_tracking"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "fraud case management",
            "fraud policy",
            "fraud monitoring rules",
            "issue register",
            "fraud governance"
        ],
        "top_k": 5
    },
    "screening_singapore_alert_workflow_gap": {
        "audit_id": "screening-singapore-alert-workflow-gap-001",
        "entity_name": "Real Singapore Screening Alert Workflow Gap",
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["SINGAPORE"],
        "entity_type": "payments_platform",
        "products": ["cross_border_payments"],
        "customer_types": ["enterprise"],
        "domains": ["transaction_screening", "sanctions", "governance"],
        "source_families": ["regulations", "sanctions", "industry_fintech"],
        "query_terms": [
            "transaction screening",
            "screening alert workflow",
            "screening escalation",
            "alert disposition",
            "screening governance"
        ],
        "top_k": 5
    },
    "licensing_hong_kong_inventory_accountability_gap": {
        "audit_id": "licensing-hong-kong-inventory-accountability-gap-001",
        "entity_name": "Real Hong Kong Licensing Inventory Accountability Gap",
        "audit_type": "regulatory_licensing_readiness_review",
        "industry": "payments",
        "jurisdictions": ["HONG_KONG"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "smb"],
        "domains": ["regulatory_licensing", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "licensing inventory",
            "regulatory accountability",
            "licensing governance",
            "ownership and accountability",
            "roles and responsibilities"
        ],
        "top_k": 5
    },
    "remediation_uae_closure_evidence_gap": {
        "audit_id": "remediation-uae-closure-evidence-gap-001",
        "entity_name": "Real UAE Remediation Closure Evidence Gap",
        "audit_type": "remediation_tracking_review",
        "industry": "fintech",
        "jurisdictions": ["UAE"],
        "entity_type": "payments_platform",
        "products": ["wallet"],
        "customer_types": ["consumer", "enterprise"],
        "domains": ["remediation_tracking", "governance"],
        "source_families": ["governance", "industry_fintech"],
        "query_terms": [
            "closure evidence",
            "issue register",
            "action tracker",
            "owner assignment",
            "remediation governance"
        ],
        "top_k": 5
    },
    "aml_australia_monitoring_escalation_gap": {
        "audit_id": "aml-australia-monitoring-escalation-gap-001",
        "entity_name": "Real Australia AML Monitoring Escalation Gap",
        "audit_type": "aml_readiness_review",
        "industry": "payments",
        "jurisdictions": ["AUSTRALIA"],
        "entity_type": "payments_platform",
        "products": ["merchant_acquiring", "wallet"],
        "customer_types": ["smb"],
        "domains": ["aml", "governance", "regulatory_reporting"],
        "source_families": ["regulations", "aml", "industry_fintech"],
        "query_terms": [
            "transaction monitoring",
            "alert escalation",
            "reporting procedure",
            "aml governance",
            "customer risk scoring"
        ],
        "top_k": 5
    },
    "kyc_canada_consumer_onboarding_partial": {
        "audit_id": "kyc-canada-consumer-onboarding-partial-001",
        "entity_name": "Real Canada Consumer Onboarding Partial",
        "audit_type": "kyc_kyb_policy_and_control_review",
        "industry": "fintech",
        "jurisdictions": ["CANADA"],
        "entity_type": "wallet_provider",
        "products": ["wallet"],
        "customer_types": ["consumer"],
        "domains": ["kyc_kyb", "governance"],
        "source_families": ["regulations", "aml", "kyc", "industry_fintech"],
        "query_terms": [
            "cip policy",
            "identity verification workflow",
            "consumer onboarding",
            "customer risk scoring",
            "governance framework"
        ],
        "top_k": 5
    },
    "vendor_australia_licensing_vendor_partial": {
        "audit_id": "vendor-australia-licensing-vendor-partial-001",
        "entity_name": "Real Australia Licensing Vendor Partial",
        "audit_type": "vendor_internal_compliance_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["AUSTRALIA"],
        "entity_type": "vendor",
        "products": ["api", "dashboard"],
        "customer_types": ["enterprise"],
        "domains": ["vendor_risk", "regulatory_licensing", "governance"],
        "source_families": ["vendor_risk", "governance", "industry_fintech"],
        "query_terms": [
            "vendor due diligence procedure",
            "licensing obligations",
            "vendor monitoring cadence",
            "regulatory mapping",
            "outsourcing governance"
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
        f"# {case_id}\n\n## Scenario\nReal corpus-backed gold case.\n\n## Human adjudication\nTo be completed after deterministic run review.\n\n## Reviewer rationale\nComplete after reviewing initial_run_output.json.\n",
        encoding="utf-8"
    )
    print("seeded", case_id)
