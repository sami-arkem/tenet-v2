from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.remediation_lifecycle import (
    apply_verification_result,
    load_lifecycle_items,
    load_timeline,
    recompute_lifecycle_artifacts,
    write_lifecycle_gate,
    write_lifecycle_index,
    write_lifecycle_items,
    write_timeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply remediation re-verification result.")
    parser.add_argument("--items", default="state/remediation/remediation_items.jsonl")
    parser.add_argument("--timeline", default="state/remediation/remediation_timeline.jsonl")
    parser.add_argument("--index", default="state/remediation/remediation_lifecycle_index.json")
    parser.add_argument("--gate", default="state/remediation/remediation_gate.json")
    parser.add_argument("--remediation-id", required=True)
    parser.add_argument("--verification-passed", required=True, choices=["true", "false"])
    parser.add_argument("--updated-gap-note", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = load_lifecycle_items(Path(args.items))
    timeline = load_timeline(Path(args.timeline))

    updated_items, updated_timeline = apply_verification_result(
        lifecycle_items=items,
        timeline=timeline,
        remediation_id=args.remediation_id,
        verification_passed=(args.verification_passed == "true"),
        updated_gap_note=args.updated_gap_note,
    )

    index_artifact, gate_artifact = recompute_lifecycle_artifacts(lifecycle_items=updated_items)

    write_lifecycle_items(Path(args.items), updated_items)
    write_timeline(Path(args.timeline), updated_timeline)
    write_lifecycle_index(Path(args.index), index_artifact)
    write_lifecycle_gate(Path(args.gate), gate_artifact)

    print(json.dumps({
        "remediation_id": args.remediation_id,
        "verification_passed": args.verification_passed == "true",
        "gate_status": gate_artifact.gate_status,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
