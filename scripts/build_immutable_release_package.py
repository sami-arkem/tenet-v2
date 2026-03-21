from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.immutable_release_package import (
    build_immutable_release_package,
    load_artifact,
    write_immutable_release_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build immutable release package manifest only when finalize decision passes."
    )
    parser.add_argument(
        "--finalize-decision",
        default="state/finalize/finalize_decision.json",
        help="Path to finalize decision JSON.",
    )
    parser.add_argument(
        "--manifest-output",
        default="state/finalize/immutable_release_package.json",
        help="Path to immutable release package JSON.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Repeatable artifact path to include in release package when finalize passes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    finalize_decision = load_artifact(Path(args.finalize_decision))
    files_to_include = [Path(p) for p in args.include]

    artifact = build_immutable_release_package(
        finalize_decision=finalize_decision,
        files_to_include=files_to_include,
        manifest_path=Path(args.manifest_output),
    )
    write_immutable_release_package(Path(args.manifest_output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0 if artifact.package_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
