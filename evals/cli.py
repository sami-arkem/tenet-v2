from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.runner import run_eval_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Tenet eval suite against real gold cases.")
    parser.add_argument("--base-dir", default="evals/gold_cases", help="Directory containing real gold cases")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    args = parser.parse_args()

    summary = run_eval_suite(base_dir=args.base_dir)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
