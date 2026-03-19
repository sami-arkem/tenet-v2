from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.finalize_hard_blocker import (
    build_finalize_decision,
    load_artifact,
    write_finalize_decision,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hard-block release finalization unless finalize_release_artifact passes."
    )
    parser.add_argument(
        "--finalize-artifact",
        default="state/finalize/finalize_release_artifact.json",
        help="Path to finalize release artifact JSON.",
    )
    parser.add_argument(
        "--release-package-path",
        default="state/finalize/release_package.json",
        help="Release package path to permit only on PASS.",
    )
    parser.add_argument(
        "--decision-output",
        default="state/finalize/finalize_decision.json",
        help="Path to finalize decision JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    finalize_artifact = load_artifact(Path(args.finalize_artifact))
    decision = build_finalize_decision(
        finalize_release_artifact=finalize_artifact,
        release_package_path=args.release_package_path,
    )
    write_finalize_decision(Path(args.decision_output), decision)
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0 if decision.finalize_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
