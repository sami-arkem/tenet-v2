from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.canonical_audit_runner import (
    append_jobs,
    build_audit_runner_outputs,
    load_audit_runner_state,
    load_existing_jobs,
    load_work_items,
    save_audit_runner_state,
    write_runner_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue canonical audit runner jobs from workflow work items."
    )
    parser.add_argument(
        "--work-items",
        default="state/audit_workflow/work_items.jsonl",
        help="Path to audit workflow work items JSONL.",
    )
    parser.add_argument(
        "--state",
        default="state/audit_runner/runner_state.json",
        help="Path to audit runner state JSON.",
    )
    parser.add_argument(
        "--jobs",
        default="state/audit_runner/jobs.jsonl",
        help="Path to audit runner jobs JSONL.",
    )
    parser.add_argument(
        "--index",
        default="state/audit_runner/runner_index.json",
        help="Path to audit runner index JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    work_items = load_work_items(Path(args.work_items))
    existing_jobs = load_existing_jobs(Path(args.jobs))
    state = load_audit_runner_state(Path(args.state))

    result, next_state = build_audit_runner_outputs(
        work_items=work_items,
        existing_jobs=existing_jobs,
        state=state,
    )

    append_jobs(jobs=result.created_jobs, path=Path(args.jobs))
    if result.runner_index is not None:
        write_runner_index(Path(args.index), result.runner_index)
    save_audit_runner_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
