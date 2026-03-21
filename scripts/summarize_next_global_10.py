import json
from pathlib import Path

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
Path("logs/next_global_10_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

for row in summary:
    print("=" * 100)
    print("CASE:", row["case_id"])
    print("decision:", row["decision"])
    print("regimes:", row["regimes"])
    print("missing_controls:", row["missing_controls"])
    print("missing_evidence:", row["missing_evidence"])
    print("findings:", row["findings"])
    print("coverage:", row["coverage"])
