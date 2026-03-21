from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit_workflow_intake import (
    append_audit_workflow_work_items,
    build_audit_workflow_intake_outputs,
    load_audit_workflow_intake_state,
    load_existing_work_items,
    load_materialized_audit_records,
    save_audit_workflow_intake_state,
    write_audit_workflow_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Intake materialized scheduled audits into canonical audit workflow work items."
    )
    parser.add_argument(
        "--materialized-records",
        default="state/audit_schedule/materialized_audit_records.jsonl",
        help="Path to materialized audit records JSONL.",
    )
    parser.add_argument(
        "--state",
        default="state/audit_workflow/intake_state.json",
        help="Path to workflow intake state JSON.",
    )
    parser.add_argument(
        "--work-items",
        default="state/audit_workflow/work_items.jsonl",
        help="Path to workflow work items JSONL.",
    )
    parser.add_argument(
        "--index",
        default="state/audit_workflow/workflow_index.json",
        help="Path to workflow index JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    materialized_records = load_materialized_audit_records(Path(args.materialized_records))
    existing_work_items = load_existing_work_items(Path(args.work_items))
    state = load_audit_workflow_intake_state(Path(args.state))

    result, next_state = build_audit_workflow_intake_outputs(
        materialized_audit_records=materialized_records,
        existing_work_items=existing_work_items,
        state=state,
    )

    append_audit_workflow_work_items(
        work_items=result.created_work_items,
        path=Path(args.work_items),
    )
    if result.workflow_index is not None:
        write_audit_workflow_index(Path(args.index), result.workflow_index)
    save_audit_workflow_intake_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
