from pathlib import Path
import json

CASES = [
    "aml_uae_policy_governance_gap",
    "kyb_singapore_beneficial_ownership_gap",
    "sanctions_uae_wallet_screening_partial",
    "governance_canada_committee_roles_gap",
    "vendor_hong_kong_outsourcing_monitoring_gap",
    "fraud_uae_case_management_partial",
    "screening_singapore_alert_workflow_gap",
    "licensing_hong_kong_inventory_accountability_gap",
    "remediation_uae_closure_evidence_gap",
    "aml_australia_monitoring_escalation_gap",
    "kyc_canada_consumer_onboarding_partial",
    "vendor_australia_licensing_vendor_partial",
]

def test_gold_case_push_to_50_files_exist():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        assert (case_dir / "audit_context.json").exists()
        assert (case_dir / "expected_assertions.json").exists()
        assert (case_dir / "case_notes.md").exists()

def test_gold_case_push_to_50_contexts_have_domains_and_jurisdictions():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        ctx = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
        assert ctx.get("jurisdictions")
        assert ctx.get("domains")
        assert isinstance(ctx["jurisdictions"], list)
        assert isinstance(ctx["domains"], list)
