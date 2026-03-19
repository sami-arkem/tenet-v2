from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.reason_output_bridge import (
    build_canonical_reason_artifact_bundle,
    load_reason_outputs,
    write_canonical_reason_artifact_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge raw deterministic reason.py outputs into canonical_reason_artifact_v1 bundle."
    )
    parser.add_argument(
        "--reason-output",
        required=True,
        help="Path to raw reason.py output JSON or JSONL.",
    )
    parser.add_argument(
        "--output",
        default="state/audit_execution/canonical_reason_artifacts.json",
        help="Path to canonical reason artifact bundle JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_outputs = load_reason_outputs(Path(args.reason_output))
    bundle = build_canonical_reason_artifact_bundle(raw_outputs)
    write_canonical_reason_artifact_bundle(Path(args.output), bundle)
    print(json.dumps(bundle.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
