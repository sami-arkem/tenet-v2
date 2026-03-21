from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit_schedule_execution_bridge import (
    append_audit_creation_requests,
    build_execution_bridge_outputs,
    load_due_execution_queue,
    load_execution_bridge_state,
    load_readiness_alerts,
    load_readiness_snapshot,
    save_execution_bridge_state,
    write_schedule_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge audit schedule delivery artifacts into audit workflow intake and final execution schedule gate."
    )
    parser.add_argument(
        "--queue",
        default="state/audit_schedule/due_execution_queue.jsonl",
        help="Path to due execution queue JSONL.",
    )
    parser.add_argument(
        "--alerts",
        default="state/audit_schedule/readiness_alerts.jsonl",
        help="Path to readiness alerts JSONL.",
    )
    parser.add_argument(
        "--snapshot",
        default="state/audit_schedule/readiness_snapshot.json",
        help="Path to readiness snapshot JSON.",
    )
    parser.add_argument(
        "--state",
        default="state/audit_schedule/execution_bridge_state.json",
        help="Path to execution bridge state JSON.",
    )
    parser.add_argument(
        "--requests",
        default="state/audit_schedule/audit_creation_requests.jsonl",
        help="Path to audit creation requests JSONL.",
    )
    parser.add_argument(
        "--gate",
        default="state/audit_schedule/final_execution_schedule_gate.json",
        help="Path to schedule gate JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    due_execution_queue = load_due_execution_queue(Path(args.queue))
    readiness_alerts = load_readiness_alerts(Path(args.alerts))
    readiness_snapshot = load_readiness_snapshot(Path(args.snapshot))
    state = load_execution_bridge_state(Path(args.state))

    result, next_state = build_execution_bridge_outputs(
        due_execution_queue=due_execution_queue,
        readiness_snapshot=readiness_snapshot,
        readiness_alerts=readiness_alerts,
        state=state,
    )

    append_audit_creation_requests(
        requests=result.audit_creation_requests,
        path=Path(args.requests),
    )
    if result.schedule_gate is not None:
        write_schedule_gate(Path(args.gate), result.schedule_gate)
    save_execution_bridge_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
