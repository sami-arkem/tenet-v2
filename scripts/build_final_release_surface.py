from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from core.final_release_surface import (
    build_release_surface,
    load_artifact,
    write_release_surface,
)


def _optional_artifact(path_value: Optional[str]) -> Optional[dict]:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return load_artifact(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical release surface artifact from final execution discipline and runner/report/export surfaces."
    )
    parser.add_argument(
        "--final-execution-discipline",
        default="state/final_execution/final_execution_discipline.json",
        help="Path to final execution discipline JSON.",
    )
    parser.add_argument(
        "--runner-index",
        default="state/audit_runner/runner_index.json",
        help="Path to runner index JSON.",
    )
    parser.add_argument(
        "--report-gate",
        default=None,
        help="Optional path to report validation gate JSON.",
    )
    parser.add_argument(
        "--export-gate",
        default=None,
        help="Optional path to export gate JSON.",
    )
    parser.add_argument(
        "--output",
        default="state/release_surface/release_surface.json",
        help="Path to final release surface JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    final_execution_discipline = load_artifact(Path(args.final_execution_discipline))
    runner_index = load_artifact(Path(args.runner_index))
    report_gate = _optional_artifact(args.report_gate)
    export_gate = _optional_artifact(args.export_gate)

    artifact = build_release_surface(
        final_execution_discipline=final_execution_discipline,
        runner_index=runner_index,
        report_gate=report_gate,
        export_gate=export_gate,
    )
    write_release_surface(Path(args.output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
