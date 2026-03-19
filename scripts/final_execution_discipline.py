from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.io_utils import atomic_write_json


SUMMARY_PATH = Path("logs/final_execution_summary.json")
STEP_TIMEOUT_SECONDS = 900


def _base_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "."
    return env


def _parse_json_text(text: str) -> Any:
    return json.loads((text or "").strip())


def run_step(
    name: str,
    cmd: List[str],
    env: Dict[str, str] | None = None,
    timeout_seconds: int = STEP_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout_seconds,
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nStep timed out after {timeout_seconds} seconds."
        timed_out = True

    return {
        "name": name,
        "command": cmd,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
        "passed": returncode == 0,
    }


def load_json_if_exists(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _step_by_name(steps: List[Dict[str, Any]], name: str) -> Dict[str, Any] | None:
    for step in steps:
        if step["name"] == name:
            return step
    return None


def _json_from_step_stdout(steps: List[Dict[str, Any]], name: str) -> Any:
    step = _step_by_name(steps, name)
    if not step or not step.get("passed"):
        return None
    try:
        return _parse_json_text(step.get("stdout", ""))
    except Exception:
        return None


def main() -> int:
    steps: List[Dict[str, Any]] = []

    py_compile_targets = [
        "src/core/io_utils.py",
        "src/core/library_loader.py",
        "src/core/pack_loader.py",
        "src/core/pack_composer.py",
        "src/core/retrieval_preparation.py",
        "src/core/pack_runtime.py",
        "src/memory/audit_memory.py",
        "src/memory/remediation_memory.py",
        "src/memory/trend_intelligence.py",
        "src/memory/historical_context.py",
        "src/reporting/build_report_pack.py",
        "src/reporting/deterministic_report_builder.py",
        "src/workflow/evidence_pack_loader.py",
        "src/workflow/workflow_runner.py",
        "src/workflow/readiness.py",
        "scripts/run_live_model_evals.py",
        "scripts/run_customer_pack_stability_suite.py",
        "scripts/summarize_customer_pack_stability.py",
        "scripts/run_customer_evidence_pack.py",
        "scripts/run_readiness_check.py",
        "scripts/proof_expansion_pipeline.py",
        "scripts/proof_batch_import.py",
        "scripts/proof_density_lane.py",
        "scripts/smoke_boardroom_historical_reporting.py",
    ]

    steps.append(run_step(
        "py_compile",
        [sys.executable, "-m", "py_compile", *py_compile_targets],
    ))

    steps.append(run_step(
        "pytest",
        [sys.executable, "-m", "pytest", "-q"],
    ))

    steps.append(run_step(
        "readiness_check",
        [sys.executable, "scripts/run_readiness_check.py"],
        env=_base_env(),
    ))

    steps.append(run_step(
        "live_model_evals",
        [sys.executable, "scripts/run_live_model_evals.py"],
        env=_base_env(),
    ))

    steps.append(run_step(
        "customer_pack_stability_suite",
        [sys.executable, "scripts/run_customer_pack_stability_suite.py"],
        env=_base_env(),
    ))

    steps.append(run_step(
        "customer_pack_stability_summary",
        [sys.executable, "scripts/summarize_customer_pack_stability.py"],
        env=_base_env(),
    ))

    steps.append(run_step(
        "workflow_smoke_customer_pack",
        [sys.executable, "scripts/run_customer_evidence_pack.py", "data/customer_evidence_packs/demo_enterprise_pack"],
        env=_base_env(),
    ))

    steps.append(run_step(
        "historical_reporting_smoke",
        [sys.executable, "scripts/smoke_boardroom_historical_reporting.py"],
        env=_base_env(),
    ))

    all_passed = all(step["passed"] for step in steps)

    readiness = _json_from_step_stdout(steps, "readiness_check")
    if readiness is None:
        readiness = load_json_if_exists("logs/customer_pack_stability/readiness_after_customer_stability.json")

    eval_summary = load_json_if_exists("logs/evals/live_model_eval_summary.json")
    customer_pack_summary = _json_from_step_stdout(steps, "customer_pack_stability_summary")
    if customer_pack_summary is None:
        customer_pack_summary = load_json_if_exists("logs/customer_pack_stability/summary.json")
    boardroom_pack = load_json_if_exists("logs/boardroom_historical_report_pack.json")

    final_summary = {
        "summary_version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_steps_passed": all_passed,
        "steps": [
            {
                "name": step["name"],
                "passed": step["passed"],
                "returncode": step["returncode"],
                "timed_out": step["timed_out"],
                "duration_seconds": step["duration_seconds"],
            }
            for step in steps
        ],
        "readiness": readiness,
        "eval": {
            "case_count": len(eval_summary or []),
            "failed_count": sum(1 for row in (eval_summary or []) if not row.get("passed")),
            "min_weighted_score": min((row.get("weighted_score", 0.0) for row in (eval_summary or [])), default=0.0),
        },
        "customer_pack_stability": customer_pack_summary,
        "boardroom_historical_reporting": {
            "board_history_label": (((boardroom_pack or {}).get("board_memo") or {}).get("historical_context") or {}).get("label"),
            "regulator_history_label": (((boardroom_pack or {}).get("regulator_memo") or {}).get("historical_context") or {}).get("label"),
            "client_history_label": (((boardroom_pack or {}).get("client_report") or {}).get("historical_context") or {}).get("label"),
        },
    }

    atomic_write_json(SUMMARY_PATH, final_summary)
    print(json.dumps(final_summary, indent=2))

    if not all_passed:
        failed = [step["name"] for step in steps if not step["passed"]]
        print(f"FAILED STEPS: {failed}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
