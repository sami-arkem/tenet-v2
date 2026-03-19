import json
from pathlib import Path

from src.core.pack_runtime import build_runtime_retrieval_inputs, enrich_audit_plan_with_packs
from src.reasoning.audit_plan import build_audit_plan

cases = [
    {
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "entity_name": "Real AML Case 001",
        "query_terms": ["aml policy"],
    },
    {
        "audit_type": "transaction_screening_review",
        "industry": "payments",
        "jurisdictions": ["CANADA"],
        "entity_name": "Real Canada Transaction Screening Governance Partial",
        "query_terms": ["transaction screening"],
    },
    {
        "audit_type": "remediation_tracking_review",
        "industry": "payments",
        "jurisdictions": ["CANADA"],
        "entity_name": "Real Canada Remediation Issue Register Gap",
        "query_terms": ["issue register"],
    },
]

Path("logs").mkdir(exist_ok=True)
rows = []

for ctx in cases:
    plan = enrich_audit_plan_with_packs(ctx, build_audit_plan(ctx))
    prep = build_runtime_retrieval_inputs(ctx, plan)

    row = {
        "entity_name": ctx["entity_name"],
        "audit_type": ctx["audit_type"],
        "has_history": prep["historical_context"]["has_history"],
        "prior_recurring_missing_controls": prep["historical_context"].get("prior_recurring_missing_controls", []),
        "prior_recurring_findings": prep["historical_context"].get("prior_recurring_findings", []),
        "prior_decision_trajectory": prep["historical_context"].get("prior_decision_trajectory", {}),
        "prior_remediation_trajectory": prep["historical_context"].get("prior_remediation_trajectory", {}),
        "query_terms_count": len(prep["query_terms"]),
    }
    rows.append(row)
    print("=" * 100)
    print(json.dumps(row, indent=2))

Path("logs/historical_context_integration_smoke.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
