import json
from pathlib import Path

from src.reasoning.reason import reason
from src.core.pack_runtime import build_runtime_retrieval_inputs
from src.reasoning.audit_plan import build_audit_plan
from src.core.pack_runtime import enrich_audit_plan_with_packs

CASES = [
    ("fraud_readiness_review", "US", ["fraud", "governance"], "fraud_us_monitoring_partial"),
    ("transaction_screening_review", "EU", ["transaction_screening", "sanctions", "governance"], "screening_eu_quality_checks_gap"),
    ("regulatory_licensing_readiness_review", "UAE", ["regulatory_licensing", "vendor_risk", "governance"], "licensing_uae_vendor_readiness"),
    ("remediation_tracking_review", "CANADA", ["remediation_tracking", "governance"], "remediation_canada_closure_partial"),
]

Path("logs/future_pack_smoke").mkdir(parents=True, exist_ok=True)

for audit_type, jurisdiction, domains, case_id in CASES:
    ctx = json.loads(Path(f"evals/gold_cases/{case_id}/audit_context.json").read_text(encoding="utf-8"))
    ctx["audit_type"] = audit_type
    ctx["jurisdictions"] = [jurisdiction]
    ctx["domains"] = domains

    plan = build_audit_plan(ctx)
    plan = enrich_audit_plan_with_packs(ctx, plan)
    prep = build_runtime_retrieval_inputs(ctx, plan)

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

    Path(f"logs/future_pack_smoke/{case_id}_runtime_inputs.json").write_text(
        json.dumps(prep, indent=2), encoding="utf-8"
    )
    Path(f"logs/future_pack_smoke/{case_id}_audit_output.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )

    print("=" * 100)
    print("case_id:", case_id)
    print("audit_type:", audit_type)
    print("jurisdiction:", jurisdiction)
    print("domains:", prep["domains"])
    print("regimes:", prep["regimes"])
    print("controls:", prep["controls"])
    print("decision:", out["deployment_decision"]["status"])
