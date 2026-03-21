import json
from pathlib import Path

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

summary = []
for case_id in CASES:
    case_dir = Path("evals/gold_cases") / case_id
    out = json.loads((case_dir / "initial_run_output.json").read_text(encoding="utf-8"))
    row = {
        "case_id": case_id,
        "decision": out["deployment_decision"]["status"],
        "regimes": out["regulatory_applicability"]["primary_regimes"],
        "missing_controls": [x.get("control_id") for x in out.get("missing_controls", [])],
        "missing_evidence": [x.get("control_id") or x.get("title") for x in out.get("missing_evidence", [])],
        "findings": [x.get("control_id") for x in out.get("findings", [])],
        "coverage": out["control_assessment"]["control_coverage_score"],
    }
    summary.append(row)

Path("logs").mkdir(exist_ok=True)
Path("logs/gold_case_push_to_50_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

for row in summary:
    print("=" * 100)
    print("CASE:", row["case_id"])
    print("decision:", row["decision"])
    print("regimes:", row["regimes"])
    print("missing_controls:", row["missing_controls"])
    print("missing_evidence:", row["missing_evidence"])
    print("findings:", row["findings"])
    print("coverage:", row["coverage"])
