import json
from pathlib import Path
from src.reasoning.reason import reason

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

for case_id in CASES:
    case_dir = Path("evals/gold_cases") / case_id
    ctx = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))

    out = reason(
        audit_context=ctx,
        reasoner=None,
        runtime_config={
            "enable_model_reasoning": False,
            "model_overlay_sections": [],
            "fallback_to_deterministic_on_model_error": True,
            "require_retrieved_chunks_for_model_reasoning": True,
        },
    )

    out_path = case_dir / "initial_run_output.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=" * 100)
    print(case_id)
    print("decision:", out["deployment_decision"]["status"])
    print("regimes:", out["regulatory_applicability"]["primary_regimes"])
    print("missing_controls:", [x.get("control_id") for x in out.get("missing_controls", [])])
    print("missing_evidence:", [x.get("control_id") or x.get("title") for x in out.get("missing_evidence", [])])
    print("findings:", [x.get("control_id") for x in out.get("findings", [])])
    print("coverage:", out["control_assessment"]["control_coverage_score"])
