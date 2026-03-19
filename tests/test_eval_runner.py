import json
from pathlib import Path

from evals.runner import run_eval_suite


def test_run_eval_suite_on_real_contract_shape(tmp_path: Path):
    case_dir = tmp_path / "real_case_001"
    case_dir.mkdir(parents=True)

    (case_dir / "audit_context.json").write_text(json.dumps({
        "audit_id": "real-case-001",
        "entity_name": "Real Case Entity",
        "audit_type": "aml_readiness_review",
        "industry": "fintech",
        "jurisdictions": ["US"],
        "source_families": ["regulations", "aml", "enforcement", "industry_fintech"],
        "query_terms": ["aml", "controls"],
        "top_k": 8
    }), encoding="utf-8")

    (case_dir / "expected_assertions.json").write_text(json.dumps({
        "case_id": "real_case_001",
        "expected": {
            "equals": {
                "deployment_decision.status": "BLOCKED"
            }
        }
    }), encoding="utf-8")

    (case_dir / "case_notes.md").write_text(
        "This test only validates eval harness execution against the real contract shape.",
        encoding="utf-8"
    )

    summary = run_eval_suite(base_dir=str(tmp_path))
    assert summary["case_count"] == 1
    assert summary["results"][0]["case_id"] == "real_case_001"
