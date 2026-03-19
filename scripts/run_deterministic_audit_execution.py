from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.deterministic_audit_execution_bridge import (
    append_execution_records,
    build_execution_outputs,
    load_execution_outcomes,
    load_execution_state,
    load_existing_execution_records,
    load_jobs,
    save_execution_state,
    write_execution_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic audit execution records from canonical audit runner jobs."
    )
    parser.add_argument(
        "--jobs",
        default="state/audit_runner/jobs.jsonl",
        help="Path to audit runner jobs JSONL.",
    )
    parser.add_argument(
        "--outcomes",
        default=None,
        help="Optional path to deterministic job outcomes JSON.",
    )
    parser.add_argument(
        "--state",
        default="state/audit_execution/execution_state.json",
        help="Path to audit execution state JSON.",
    )
    parser.add_argument(
        "--records",
        default="state/audit_execution/execution_records.jsonl",
        help="Path to audit execution records JSONL.",
    )
    parser.add_argument(
        "--index",
        default="state/audit_execution/execution_index.json",
        help="Path to audit execution index JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    jobs = load_jobs(Path(args.jobs))
    outcomes = load_execution_outcomes(Path(args.outcomes)) if args.outcomes else {}
    existing_records = load_existing_execution_records(Path(args.records))
    state = load_execution_state(Path(args.state))

    result, next_state = build_execution_outputs(
        jobs=jobs,
        execution_outcomes=outcomes,
        existing_execution_records=existing_records,
        state=state,
    )

    append_execution_records(records=result.created_execution_records, path=Path(args.records))
    if result.execution_index is not None:
        write_execution_index(Path(args.index), result.execution_index)
    save_execution_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
