from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_lifecycle import (
    load_lifecycle_items,
    load_timeline,
    recompute_lifecycle_artifacts,
    transition_status,
    submit_for_verification,
    write_lifecycle_gate,
    write_lifecycle_index,
    write_lifecycle_items,
    write_timeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transition remediation status.")
    parser.add_argument("--items", default="state/remediation/remediation_items.jsonl")
    parser.add_argument("--timeline", default="state/remediation/remediation_timeline.jsonl")
    parser.add_argument("--index", default="state/remediation/remediation_lifecycle_index.json")
    parser.add_argument("--gate", default="state/remediation/remediation_gate.json")
    parser.add_argument("--remediation-id", required=True)
    parser.add_argument("--to-status", required=True)
    parser.add_argument("--actor-user-id", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--evidence-file-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = load_lifecycle_items(Path(args.items))
    timeline = load_timeline(Path(args.timeline))

    if args.to_status == "EVIDENCE_SUBMITTED":
        updated_items, updated_timeline = submit_for_verification(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=args.remediation_id,
            actor_user_id=args.actor_user_id,
            note=args.note,
            evidence_file_ids=args.evidence_file_id,
        )
    else:
        updated_items, updated_timeline = transition_status(
            lifecycle_items=items,
            timeline=timeline,
            remediation_id=args.remediation_id,
            to_status=args.to_status,
            actor_user_id=args.actor_user_id,
            note=args.note,
            evidence_file_ids=args.evidence_file_id,
        )

    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items)

    write_lifecycle_items(Path(args.items), updated_items)
    write_timeline(Path(args.timeline), updated_timeline)
    write_lifecycle_index(Path(args.index), index_artifact)
    write_lifecycle_gate(Path(args.gate), gate_artifact)

    print(json.dumps({
        "remediation_id": args.remediation_id,
        "to_status": args.to_status,
        "gate_status": gate_artifact.gate_status,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
