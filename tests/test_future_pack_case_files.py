from pathlib import Path
import json

CASES = [
    "fraud_us_monitoring_partial",
    "fraud_uk_case_management_gap",
    "screening_us_transaction_partial",
    "screening_eu_quality_checks_gap",
    "licensing_uae_vendor_readiness",
    "licensing_singapore_governance_partial",
    "remediation_us_issue_tracker_gap",
    "remediation_canada_closure_partial",
    "screening_hk_false_positive_review",
    "fraud_australia_governance_heavy",
]

def test_future_pack_cases_have_required_files():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        assert (case_dir / "audit_context.json").exists()
        assert (case_dir / "expected_assertions.json").exists()
        assert (case_dir / "case_notes.md").exists()

def test_future_pack_audit_contexts_have_domains():
    for case_id in CASES:
        case_dir = Path("evals/gold_cases") / case_id
        ctx = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
        assert ctx.get("domains")
        assert isinstance(ctx["domains"], list)
