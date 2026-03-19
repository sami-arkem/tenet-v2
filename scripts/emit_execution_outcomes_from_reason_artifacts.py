from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.reason_artifact_adapter import (
    build_canonical_execution_outcomes,
    load_reason_artifacts,
    write_canonical_execution_outcomes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit canonical execution outcomes from canonical deterministic reason artifacts."
    )
    parser.add_argument(
        "--reason-artifacts",
        required=True,
        help="Path to canonical reason artifact JSON or JSONL.",
    )
    parser.add_argument(
        "--output",
        default="state/audit_execution/execution_outcomes.json",
        help="Path to canonical execution outcomes JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_artifacts = load_reason_artifacts(Path(args.reason_artifacts))
    
    # If the file is a canonical reason artifact bundle, extract the artifacts
    if not raw_artifacts:
        payload = json.loads(Path(args.reason_artifacts).read_text(encoding="utf-8"))
        if isinstance(payload.get("canonical_reason_artifacts"), list):
            raw_artifacts = payload["canonical_reason_artifacts"]
    
    artifact = build_canonical_execution_outcomes(raw_artifacts)
    write_canonical_execution_outcomes(Path(args.output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
