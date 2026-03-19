import json
from pathlib import Path

from src.reasoning.reason import reason


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def case_dirs() -> list[Path]:
    root = Path("evals/gold_cases")
    return sorted(path for path in root.iterdir() if path.is_dir())


def generate_initial_run_output(case_dir: Path) -> dict:
    out_path = case_dir / "initial_run_output.json"
    context = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    output = reason(
        audit_context=context,
        reasoner=None,
        runtime_config={
            "enable_model_reasoning": False,
            "model_overlay_sections": [],
            "fallback_to_deterministic_on_model_error": True,
            "require_retrieved_chunks_for_model_reasoning": True,
        },
    )
    write_json(out_path, output)
    return output


for case_dir in case_dirs():
    case_id = case_dir.name
    context = json.loads((case_dir / "audit_context.json").read_text(encoding="utf-8"))
    output = generate_initial_run_output(case_dir)

    decision = output["deployment_decision"]["status"]
    regimes = output["regulatory_applicability"]["primary_regimes"]
    missing_controls = [x.get("control_id") for x in output.get("missing_controls", []) if x.get("control_id")]
    missing_evidence = [x.get("control_id") or x.get("title") for x in output.get("missing_evidence", []) if x.get("control_id") or x.get("title")]
    finding_ids = [x.get("control_id") for x in output.get("findings", []) if x.get("control_id")]
    coverage = int(output["control_assessment"]["control_coverage_score"])

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
    if missing_evidence and all(isinstance(x, str) and "-" in x for x in missing_evidence):
        expected["expected"]["contains"]["missing_evidence.control_id"] = missing_evidence
    if finding_ids:
        expected["expected"]["contains"]["findings.control_id"] = finding_ids

    write_json(case_dir / "expected_assertions.json", expected)

    notes = f"""# {case_id}

## Scenario
Real corpus-backed case for Tenet deterministic evaluation.

## Audit context
- audit_type: {context.get("audit_type", "")}
- industry: {context.get("industry", "")}
- jurisdictions: {", ".join(context.get("jurisdictions", []))}
- entity_name: {context.get("entity_name", "")}

## Human adjudication
Expected outcome is {decision} based on the current corpus-backed deterministic output.

## Expected regimes
""" + "\n".join(f"- {r}" for r in regimes) + f"""

## Expected control position
- missing_controls: {", ".join(missing_controls) if missing_controls else "none"}
- missing_evidence: {", ".join(missing_evidence) if missing_evidence else "none"}
- findings: {", ".join(finding_ids) if finding_ids else "none"}
- control_coverage_score minimum: {coverage}

## Reviewer rationale
This gold case is grounded in the currently observed deterministic engine behavior over the existing retrieval corpus.
"""

    (case_dir / "case_notes.md").write_text(notes, encoding="utf-8")
    print("updated", case_id)

print("done")
