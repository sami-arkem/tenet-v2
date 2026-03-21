from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_operator_service import (
    RemediationOperatorPaths,
    load_actor_directory,
    set_due_date_api,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set remediation due date.")
    parser.add_argument("--actor-directory", required=True)
    parser.add_argument("--actor-user-id", required=True)
    parser.add_argument("--remediation-id", required=True)
    parser.add_argument("--due-date", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--items", default="state/remediation/remediation_items_operator.jsonl")
    parser.add_argument("--timeline", default="state/remediation/remediation_timeline.jsonl")
    parser.add_argument("--index", default="state/remediation/remediation_lifecycle_index.json")
    parser.add_argument("--gate", default="state/remediation/remediation_gate.json")
    parser.add_argument("--evidence-metadata", default="state/remediation/remediation_evidence_metadata.jsonl")
    parser.add_argument("--notification-outbox", default="state/remediation/remediation_notification_outbox.jsonl")
    parser.add_argument("--operator-audit-log", default="state/remediation/remediation_operator_audit_log.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    actors = load_actor_directory(Path(args.actor_directory))
    result = set_due_date_api(
        actor_directory=actors,
        actor_user_id=args.actor_user_id,
        remediation_id=args.remediation_id,
        due_date=args.due_date,
        note=args.note,
        operator_paths=RemediationOperatorPaths(
            items=args.items,
            timeline=args.timeline,
            lifecycle_index=args.index,
            gate=args.gate,
            evidence_metadata=args.evidence_metadata,
            notification_outbox=args.notification_outbox,
            operator_audit_log=args.operator_audit_log,
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
