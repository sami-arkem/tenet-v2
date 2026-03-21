import json
from pathlib import Path
from src.reasoning.reason import reason

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
