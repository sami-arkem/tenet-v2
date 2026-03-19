from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_lifecycle import load_lifecycle_items
from core.remediation_due_planner import (
    load_notification_outbox,
    plan_due_notifications,
    write_notification_outbox,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan remediation due-soon and overdue notification events.")
    parser.add_argument("--items", default="state/remediation/remediation_items_operator.jsonl")
    parser.add_argument("--outbox", default="state/remediation/remediation_notification_outbox.jsonl")
    parser.add_argument("--today", required=True)
    parser.add_argument("--now", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = load_lifecycle_items(Path(args.items))
    outbox = load_notification_outbox(Path(args.outbox))
    planned = plan_due_notifications(
        lifecycle_items=items,
        existing_outbox=outbox,
        today=args.today,
        now=args.now,
    )
    write_notification_outbox(Path(args.outbox), planned)
    print(json.dumps({
        "total_events_after_write": len(planned),
        "new_events": len(planned) - len(outbox),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
