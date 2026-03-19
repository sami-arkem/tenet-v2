from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_tracking_engine import (
    append_remediation_items,
    build_remediation_tracking_outputs,
    load_canonical_reason_artifacts,
    load_execution_records,
    load_existing_remediation_items,
    load_remediation_state,
    save_remediation_state,
    write_remediation_gate,
    write_remediation_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic remediation tracking from canonical audit artifacts."
    )
    parser.add_argument(
        "--canonical-reason-artifacts",
        default="state/audit_execution/canonical_reason_artifacts.json",
        help="Path to canonical reason artifacts JSON.",
    )
    parser.add_argument(
        "--execution-records",
        default="state/audit_execution/execution_records.jsonl",
        help="Path to execution records JSONL.",
    )
    parser.add_argument(
        "--state",
        default="state/remediation/remediation_state.json",
        help="Path to remediation state JSON.",
    )
    parser.add_argument(
        "--items",
        default="state/remediation/remediation_items.jsonl",
        help="Path to remediation items JSONL.",
    )
    parser.add_argument(
        "--index",
        default="state/remediation/remediation_index.json",
        help="Path to remediation index JSON.",
    )
    parser.add_argument(
        "--gate",
        default="state/remediation/remediation_gate.json",
        help="Path to remediation gate JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    canonical_reason_artifacts = load_canonical_reason_artifacts(Path(args.canonical_reason_artifacts))
    execution_records = load_execution_records(Path(args.execution_records))
    existing_items = load_existing_remediation_items(Path(args.items))
    state = load_remediation_state(Path(args.state))

    result, next_state = build_remediation_tracking_outputs(
        canonical_reason_artifacts=canonical_reason_artifacts,
        execution_records=execution_records,
        existing_remediation_items=existing_items,
        state=state,
    )

    append_remediation_items(items=result.created_items, path=Path(args.items))
    if result.remediation_index is not None:
        write_remediation_index(Path(args.index), result.remediation_index)
    if result.remediation_gate is not None:
        write_remediation_gate(Path(args.gate), result.remediation_gate)
    save_remediation_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.remediation_gate is not None and result.remediation_gate.remediation_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
