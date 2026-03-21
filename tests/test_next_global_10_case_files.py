from pathlib import Path
import json

CASES = [
    "uae_transaction_screening_escalation_gap",
    "singapore_fraud_monitoring_governance_partial",
    "hong_kong_transaction_screening_false_positive_partial",
    "canada_remediation_issue_register_gap",
    "australia_regulatory_licensing_vendor_governance_gap",
    "uae_regulatory_licensing_accountability_partial",
    "singapore_remediation_closure_evidence_partial",
    "hong_kong_fraud_case_management_gap",
    "canada_transaction_screening_governance_partial",
    "australia_fraud_remediation_heavy",
]

def test_next_global_case_files_exist():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        assert (case_dir / "audit_context.json").exists()
        assert (case_dir / "expected_assertions.json").exists()
        assert (case_dir / "case_notes.md").exists()

def test_next_global_case_contexts_have_future_jurisdictions_and_domains():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        ctx = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
        assert ctx.get("jurisdictions")
        assert ctx.get("domains")
        assert isinstance(ctx["jurisdictions"], list)
        assert isinstance(ctx["domains"], list)
