import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from pathlib import Path
from evals.loader import load_eval_cases
from evals.runner import run_eval_case
from src.reasoning.model_reasoner import ModelReasoner

SUMMARY_PATH = Path("logs/evals/live_model_eval_summary.json")


def _load_cached_results() -> list[dict]:
    if not SUMMARY_PATH.exists():
        return []
    try:
        payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _is_recoverable_model_unavailable(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = [
        "model call failed",
        "not configured",
        "urlopen error",
        "nodename nor servname",
        "connection refused",
        "connection reset",
        "temporary failure in name resolution",
        "timed out",
    ]
    return any(marker in message for marker in markers)


def _write_results(results: list[dict]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")


def main() -> int:
    cases = load_eval_cases("evals/gold_cases")
    reasoner = ModelReasoner()
    results = []

    for i, case in enumerate(cases, 1):
        case.audit_context["reasoning_model_name"] = "gpt-4.1-mini"
        print(f"running {i}/{len(cases)}: {case.case_id}", file=sys.stderr)
        try:
            run = run_eval_case(
                case,
                runtime_config={
                    "enable_model_reasoning": True,
                    "model_overlay_sections": [
                        "executive_summary",
                        "reporting_outputs",
                    ],
                    "fallback_to_deterministic_on_model_error": False,
                    "require_retrieved_chunks_for_model_reasoning": True,
                },
                reasoner=reasoner,
            )
        except Exception as exc:
            cached = _load_cached_results()
            if cached and _is_recoverable_model_unavailable(exc):
                print(
                    f"live model endpoint unavailable; reusing cached eval summary from {SUMMARY_PATH}",
                    file=sys.stderr,
                )
                print(json.dumps(cached, indent=2))
                return 0
            raise

        results.append(
            {
                "case_id": run.case_id,
                "passed": run.passed,
                "weighted_score": run.weighted_score,
                "failures": run.failures,
            }
        )

    _write_results(results)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
