from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.finalize_release_bridge import (
    build_finalize_release_artifact,
    load_artifact,
    load_execution_records,
    write_finalize_release_artifact,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build final release/finalize artifact from release surface and deterministic audit execution results."
    )
    parser.add_argument(
        "--release-surface",
        default="state/release_surface/release_surface.json",
        help="Path to release surface JSON.",
    )
    parser.add_argument(
        "--execution-index",
        default="state/audit_execution/execution_index.json",
        help="Path to audit execution index JSON.",
    )
    parser.add_argument(
        "--execution-records",
        default="state/audit_execution/execution_records.jsonl",
        help="Path to audit execution records JSONL.",
    )
    parser.add_argument(
        "--output",
        default="state/finalize/finalize_release_artifact.json",
        help="Path to finalize release artifact JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    release_surface = load_artifact(Path(args.release_surface))
    execution_index = load_artifact(Path(args.execution_index))
    execution_records = load_execution_records(Path(args.execution_records))

    artifact = build_finalize_release_artifact(
        release_surface=release_surface,
        execution_index=execution_index,
        execution_records=execution_records,
    )
    write_finalize_release_artifact(Path(args.output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
