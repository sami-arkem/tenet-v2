from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit_schedule_audit_materialization import (
    append_audit_workflow_records,
    build_audit_materialization_outputs,
    load_audit_creation_requests,
    load_audit_materialization_state,
    load_existing_audit_records,
    load_schedule_gate,
    save_audit_materialization_state,
    write_final_execution_dependency_gate,
    write_materialization_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize scheduled audit creation requests into concrete audit workflow records and emit final execution dependency gate."
    )
    parser.add_argument(
        "--requests",
        default="state/audit_schedule/audit_creation_requests.jsonl",
        help="Path to audit creation requests JSONL.",
    )
    parser.add_argument(
        "--schedule-gate",
        default="state/audit_schedule/final_execution_schedule_gate.json",
        help="Path to schedule runtime gate JSON.",
    )
    parser.add_argument(
        "--state",
        default="state/audit_schedule/audit_materialization_state.json",
        help="Path to audit materialization state JSON.",
    )
    parser.add_argument(
        "--audit-records",
        default="state/audit_schedule/materialized_audit_records.jsonl",
        help="Path to concrete audit workflow records JSONL.",
    )
    parser.add_argument(
        "--summary",
        default="state/audit_schedule/audit_materialization_summary.json",
        help="Path to materialization summary JSON.",
    )
    parser.add_argument(
        "--dependency-gate",
        default="state/audit_schedule/final_execution_schedule_dependency_gate.json",
        help="Path to final execution dependency gate JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    audit_creation_requests = load_audit_creation_requests(Path(args.requests))
    schedule_gate = load_schedule_gate(Path(args.schedule_gate))
    existing_audit_records = load_existing_audit_records(Path(args.audit_records))
    state = load_audit_materialization_state(Path(args.state))

    result, next_state = build_audit_materialization_outputs(
        audit_creation_requests=audit_creation_requests,
        schedule_gate=schedule_gate,
        existing_audit_records=existing_audit_records,
        state=state,
    )

    append_audit_workflow_records(
        records=result.created_records,
        path=Path(args.audit_records),
    )
    if result.materialization_summary is not None:
        write_materialization_summary(Path(args.summary), result.materialization_summary)
    if result.dependency_gate is not None:
        write_final_execution_dependency_gate(Path(args.dependency_gate), result.dependency_gate)
    save_audit_materialization_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
