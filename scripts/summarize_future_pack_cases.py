import json
from pathlib import Path

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
Path("logs/future_pack_case_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

for row in summary:
    print("=" * 100)
    print("CASE:", row["case_id"])
    print("decision:", row["decision"])
    print("regimes:", row["regimes"])
    print("missing_controls:", row["missing_controls"])
    print("missing_evidence:", row["missing_evidence"])
    print("findings:", row["findings"])
    print("coverage:", row["coverage"])
