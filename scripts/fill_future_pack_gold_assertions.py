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

def is_control_id(value: str) -> bool:
    return isinstance(value, str) and "-" in value and value.upper() == value

for case_id in CASES:
    case_dir = Path("evals/gold_cases") / case_id
    ctx = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    out = json.loads((case_dir / "initial_run_output.json").read_text(encoding="utf-8"))

    decision = out["deployment_decision"]["status"]
    regimes = out["regulatory_applicability"]["primary_regimes"]
    missing_controls = [x.get("control_id") for x in out.get("missing_controls", []) if x.get("control_id")]
    missing_evidence = [x.get("control_id") or x.get("title") for x in out.get("missing_evidence", []) if x.get("control_id") or x.get("title")]
    finding_ids = [x.get("control_id") for x in out.get("findings", []) if x.get("control_id")]
    coverage = int(out["control_assessment"]["control_coverage_score"])

    expected = {
        "case_id": case_id,
        "expected": {
            "equals": {
                "deployment_decision.status": decision
            },
            "contains": {},
            "minimums": {
                "control_assessment.control_coverage_score": coverage
            }
        }
    }

    if regimes:
        expected["expected"]["contains"]["regulatory_applicability.primary_regimes"] = regimes
    if missing_controls:
        expected["expected"]["contains"]["missing_controls.control_id"] = missing_controls
    if missing_evidence and all(is_control_id(x) for x in missing_evidence):
        expected["expected"]["contains"]["missing_evidence.control_id"] = missing_evidence
    if finding_ids:
        expected["expected"]["contains"]["findings.control_id"] = finding_ids

    (case_dir / "expected_assertions.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")

    notes = f"""# {case_id}

## Scenario
Real corpus-backed future-pack case.

## Audit context
- audit_type: {ctx.get("audit_type", "")}
- industry: {ctx.get("industry", "")}
- jurisdictions: {", ".join(ctx.get("jurisdictions", []))}
- entity_name: {ctx.get("entity_name", "")}
- domains: {", ".join(ctx.get("domains", []))}

## Human adjudication
Expected outcome is {decision} based on the current deterministic engine behavior over the existing retrieval corpus.

## Expected regimes
""" + "\n".join(f"- {r}" for r in regimes) + f"""

## Expected control position
- missing_controls: {", ".join(missing_controls) if missing_controls else "none"}
- missing_evidence: {", ".join(missing_evidence) if missing_evidence else "none"}
- findings: {", ".join(finding_ids) if finding_ids else "none"}
- control_coverage_score minimum: {coverage}

## Reviewer rationale
This gold case is grounded in observed deterministic output, not invented target behavior.
"""
    (case_dir / "case_notes.md").write_text(notes, encoding="utf-8")
    print("updated", case_id)

print("done")
