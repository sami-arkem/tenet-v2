from __future__ import annotations

import json
from pathlib import Path

from evals.runner import run_eval_suite


def main() -> None:
    summary = run_eval_suite(base_dir="evals/gold_cases")
    out_dir = Path("logs/evals")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest_eval_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
