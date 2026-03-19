import json
from pathlib import Path
from src.reasoning.reason import reason

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

    (case_dir / "initial_run_output.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=" * 100)
    print(case_id)
    print("decision:", out["deployment_decision"]["status"])
    print("regimes:", out["regulatory_applicability"]["primary_regimes"])
    print("missing_controls:", [x.get("control_id") for x in out.get("missing_controls", [])])
    print("missing_evidence:", [x.get("control_id") or x.get("title") for x in out.get("missing_evidence", [])])
    print("findings:", [x.get("control_id") for x in out.get("findings", [])])
    print("coverage:", out["control_assessment"]["control_coverage_score"])
