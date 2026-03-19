from src.core.pack_runtime import build_runtime_retrieval_inputs
from src.reasoning.audit_plan import build_audit_plan
from src.core.pack_runtime import enrich_audit_plan_with_packs

cases = [
    {
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "query_terms": ["aml policy"],
    },
    {
        "audit_type": "sanctions_readiness_review",
        "industry": "crypto",
        "jurisdictions": ["US", "EU"],
        "query_terms": ["wallet screening"],
    },
    {
        "audit_type": "vendor_internal_compliance_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US", "UK", "EU"],
        "query_terms": ["vendor monitoring cadence"],
    },
]

for ctx in cases:
    plan = build_audit_plan(ctx)
    plan = enrich_audit_plan_with_packs(ctx, plan)
    prep = build_runtime_retrieval_inputs(ctx, plan)
    print("=" * 80)
    print("audit_type:", ctx["audit_type"])
    print("regimes:", prep["regimes"])
    print("controls:", prep["controls"])
    print("domains:", prep["domains"])
    print("query_terms:", prep["query_terms"])
