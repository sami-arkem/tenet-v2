from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from core.final_execution_discipline_runner import (
    build_final_execution_discipline,
    load_gate_artifact,
    write_final_execution_discipline,
)


def _optional_gate(path_value: Optional[str]) -> Optional[dict]:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return load_gate_artifact(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical final execution discipline artifact from deterministic gate artifacts."
    )
    parser.add_argument(
        "--schedule-dependency-gate",
        default="state/audit_schedule/final_execution_schedule_dependency_gate.json",
        help="Path to schedule dependency gate JSON.",
    )
    parser.add_argument(
        "--release-gate",
        default=None,
        help="Optional path to release gate JSON.",
    )
    parser.add_argument(
        "--export-gate",
        default=None,
        help="Optional path to export gate JSON.",
    )
    parser.add_argument(
        "--report-validation-gate",
        default=None,
        help="Optional path to report validation gate JSON.",
    )
    parser.add_argument(
        "--proof-readiness-gate",
        default=None,
        help="Optional path to proof readiness gate JSON.",
    )
    parser.add_argument(
        "--output",
        default="state/final_execution/final_execution_discipline.json",
        help="Path to final execution discipline JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    schedule_dependency_gate = load_gate_artifact(Path(args.schedule_dependency_gate))
    release_gate = _optional_gate(args.release_gate)
    export_gate = _optional_gate(args.export_gate)
    report_validation_gate = _optional_gate(args.report_validation_gate)
    proof_readiness_gate = _optional_gate(args.proof_readiness_gate)

    artifact = build_final_execution_discipline(
        schedule_dependency_gate=schedule_dependency_gate,
        release_gate=release_gate,
        export_gate=export_gate,
        report_validation_gate=report_validation_gate,
        proof_readiness_gate=proof_readiness_gate,
    )

    write_final_execution_discipline(Path(args.output), artifact)
    print(json.dumps(artifact.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
