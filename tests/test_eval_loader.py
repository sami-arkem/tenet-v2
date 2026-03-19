import json
from pathlib import Path

from evals.loader import load_eval_cases


def test_load_eval_cases_reads_real_case_contract(tmp_path: Path):
    case_dir = tmp_path / "case_001"
    case_dir.mkdir(parents=True)

    (case_dir / "audit_context.json").write_text(json.dumps({
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"]
    }), encoding="utf-8")

    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "case_001",
        "expected": {
            "equals": {
                "deployment_decision.status": "BLOCKED"
            }
        }
    }), encoding="utf-8")

    (case_dir / "case_notes.md").write_text("Real-case contract structure test.", encoding="utf-8")

    cases = load_eval_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].case_id == "case_001"
    assert cases[0].audit_context["audit_type"] == "aml_readiness_review"
