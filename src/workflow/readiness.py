from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _gold_case_dirs() -> List[Path]:
    root = Path("evals/gold_cases")
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def _customer_pack_dirs() -> List[Path]:
    root = Path("data/customer_evidence_packs")
    if not root.exists():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and p.name != "_template"
    )


def build_readiness_summary() -> Dict[str, Any]:
    gold_cases = _gold_case_dirs()
    customer_packs = _customer_pack_dirs()

    full_gold_cases = [
        p for p in gold_cases
        if (p / "audit_context.json").exists()
        and (p / "expected_assertions.json").exists()
        and (p / "case_notes.md").exists()
    ]

    customer_packs_with_runs = [
        p for p in customer_packs
        if (p / "tenet_run" / "workflow_result.json").exists()
    ]

    eval_summary_path = Path("logs/evals/live_model_eval_summary.json")
    eval_summary = _read_json(eval_summary_path) if eval_summary_path.exists() else []
    eval_case_count = len(eval_summary)
    eval_pass_count = sum(1 for row in eval_summary if row.get("passed"))
    eval_fail_count = sum(1 for row in eval_summary if not row.get("passed"))
    min_weighted = min((row.get("weighted_score", 0.0) for row in eval_summary), default=0.0)

    ready_gold_case_band = 50 <= len(full_gold_cases) <= 100
    stable_live_outputs = eval_case_count > 0 and eval_fail_count == 0 and min_weighted >= 1.0
    clear_enterprise_workflow = len(customer_packs_with_runs) > 0

    return {
        "gold_case_count": len(full_gold_cases),
        "gold_case_target_band_met": ready_gold_case_band,
        "eval_case_count": eval_case_count,
        "eval_pass_count": eval_pass_count,
        "eval_fail_count": eval_fail_count,
        "eval_min_weighted_score": min_weighted,
        "stable_live_outputs": stable_live_outputs,
        "customer_pack_count": len(customer_packs),
        "customer_packs_with_completed_runs": len(customer_packs_with_runs),
        "clear_enterprise_workflow": clear_enterprise_workflow,
        "overall_readiness": all([
            ready_gold_case_band,
            stable_live_outputs,
            clear_enterprise_workflow,
        ]),
    }
