from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.reason_result_outcome_emitter import (
    build_execution_outcomes,
    load_reason_results,
    write_execution_outcomes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit canonical execution outcomes artifact from deterministic reason.py result artifacts."
    )
    parser.add_argument(
        "--reason-results",
        required=True,
        help="Path to reason result JSON or JSONL.",
    )
    parser.add_argument(
        "--output",
        default="state/audit_execution/execution_outcomes.json",
        help="Path to execution outcomes JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = load_reason_results(Path(args.reason_results))
    artifact = build_execution_outcomes(results)
    write_execution_outcomes(Path(args.output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
