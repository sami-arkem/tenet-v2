from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.audit_schedule_delivery import (
    append_delivery_outputs,
    build_delivery_artifacts,
    load_delivery_state,
    save_delivery_state,
    write_readiness_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deliver deterministic audit schedule runtime outputs into queue/outbox/readiness artifacts."
    )
    parser.add_argument("--runtime-cycle", required=True, help="Path to runtime cycle JSON.")
    parser.add_argument(
        "--state",
        default="state/audit_schedule/delivery_state.json",
        help="Path to delivery state JSON.",
    )
    parser.add_argument(
        "--queue",
        default="state/audit_schedule/due_execution_queue.jsonl",
        help="Path to due execution queue JSONL.",
    )
    parser.add_argument(
        "--outbox",
        default="state/audit_schedule/notification_outbox.jsonl",
        help="Path to notification outbox JSONL.",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_cycle = json.loads(Path(args.runtime_cycle).read_text(encoding="utf-8"))
    state = load_delivery_state(Path(args.state))
    result, next_state = build_delivery_artifacts(runtime_cycle, state=state)

    append_delivery_outputs(
        result=result,
        queue_path=Path(args.queue),
        outbox_path=Path(args.outbox),
        alerts_path=Path(args.alerts),
    )
    if result.readiness_snapshot is not None:
        write_readiness_snapshot(Path(args.snapshot), result.readiness_snapshot)
    save_delivery_state(Path(args.state), next_state)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
