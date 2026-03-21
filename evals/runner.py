from __future__ import annotations

from typing import Dict, List, Optional

from evals.contracts import EvalCase, EvalResult
from evals.loader import load_eval_cases
from evals.scoring import load_eval_policy, score_contains, score_equals, score_minimums, weighted_score
from src.reasoning.model_reasoner import ModelReasoner
from src.reasoning.reason import reason


def run_eval_case(
    case: EvalCase,
    runtime_config: Optional[Dict[str, object]] = None,
    reasoner: Optional[ModelReasoner] = None,
) -> EvalResult:
    output = reason(
        audit_context=case.audit_context,
        reasoner=reasoner,
        runtime_config=runtime_config,
    )

    eq_earned, eq_total, eq_failures = score_equals(output, case.assertions.equals)
    ct_earned, ct_total, ct_failures = score_contains(output, case.assertions.contains)
    mn_earned, mn_total, mn_failures = score_minimums(output, case.assertions.minimums)

    policy = load_eval_policy()
    weighted, weighted_possible, weighted_failures = weighted_score(
        output=output,
        assertions={
            "equals": case.assertions.equals,
            "contains": case.assertions.contains,
            "minimums": case.assertions.minimums,
        },
        policy=policy,
    )

    raw_score = eq_earned + ct_earned + mn_earned
    raw_total = eq_total + ct_total + mn_total
    threshold = float(policy.get("pass_threshold", 0.85))
    weighted_denominator = weighted_possible if weighted_possible > 0 else 1.0
    weighted_score_ratio = weighted / weighted_denominator

    failures = []
    seen = set()
    for item in eq_failures + ct_failures + mn_failures + weighted_failures:
        if item not in seen:
            seen.add(item)
            failures.append(item)

    return EvalResult(
        case_id=case.case_id,
        passed=weighted_score_ratio >= threshold,
        score=raw_score,
        max_score=raw_total,
        weighted_score=weighted_score_ratio,
        threshold=threshold,
        failures=failures,
        output=output,
    )


def run_eval_suite(
    base_dir: str = "evals/gold_cases",
    runtime_config: Optional[Dict[str, object]] = None,
    reasoner: Optional[ModelReasoner] = None,
) -> Dict[str, object]:
    cases = load_eval_cases(base_dir)
    if not cases:
        raise RuntimeError("No gold cases found. Add real adjudicated cases under evals/gold_cases/")

    results: List[EvalResult] = []
    for case in cases:
        results.append(run_eval_case(case, runtime_config=runtime_config, reasoner=reasoner))

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_weighted = sum(r.weighted_score for r in results) / len(results)

    return {
        "case_count": len(results),
        "passed": passed,
        "failed": failed,
        "average_weighted_score": round(avg_weighted, 4),
        "results": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "score": r.score,
                "max_score": r.max_score,
                "weighted_score": round(r.weighted_score, 4),
                "threshold": r.threshold,
                "failure_count": len(r.failures),
                "failures": r.failures,
            }
            for r in results
        ],
    }
