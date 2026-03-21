from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.finalization_orchestrator import (
    build_finalization_receipt,
    load_artifact,
    write_finalization_receipt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical finalization receipt from finalize decision and immutable release package."
    )
    parser.add_argument(
        "--finalize-decision",
        default="state/finalize/finalize_decision.json",
        help="Path to finalize decision JSON.",
    )
    parser.add_argument(
        "--immutable-package",
        default="state/finalize/immutable_release_package.json",
        help="Path to immutable release package JSON.",
    )
    parser.add_argument(
        "--output",
        default="state/finalize/finalization_receipt.json",
        help="Path to finalization receipt JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    finalize_decision = load_artifact(Path(args.finalize_decision))
    immutable_package = load_artifact(Path(args.immutable_package))
    receipt = build_finalization_receipt(
        finalize_decision=finalize_decision,
        immutable_release_package=immutable_package,
    )
    write_finalization_receipt(Path(args.output), receipt)
    print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    return 0 if receipt.finalization_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
