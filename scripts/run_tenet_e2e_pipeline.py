from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.tenet_e2e_orchestrator import (
    TenetE2EPaths,
    run_tenet_e2e,
    write_e2e_run_result,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the canonical Tenet deterministic end-to-end pipeline."
    )
    parser.add_argument("--raw-reason-output", required=True, help="Path to raw reason.py output JSON/JSONL.")
    parser.add_argument("--jobs", default="state/audit_runner/jobs.jsonl", help="Path to audit runner jobs JSONL.")
    parser.add_argument("--work-items", default="state/audit_workflow/work_items.jsonl", help="Path to work items JSONL.")
    parser.add_argument("--materialized-audits", default="state/audit_schedule/materialized_audit_records.jsonl", help="Path to materialized audit records JSONL.")
    parser.add_argument("--execution-state", default="state/audit_execution/execution_state.json", help="Path to execution state JSON.")
    parser.add_argument("--execution-records", default="state/audit_execution/execution_records.jsonl", help="Path to execution records JSONL.")
    parser.add_argument("--execution-index", default="state/audit_execution/execution_index.json", help="Path to execution index JSON.")
    parser.add_argument("--canonical-reason-artifacts", default="state/audit_execution/canonical_reason_artifacts.json", help="Path to canonical reason artifacts JSON.")
    parser.add_argument("--execution-outcomes", default="state/audit_execution/execution_outcomes.json", help="Path to execution outcomes JSON.")
    parser.add_argument("--remediation-state", default="state/remediation/remediation_state.json", help="Path to remediation state JSON.")
    parser.add_argument("--remediation-items", default="state/remediation/remediation_items.jsonl", help="Path to remediation items JSONL.")
    parser.add_argument("--remediation-index", default="state/remediation/remediation_index.json", help="Path to remediation index JSON.")
    parser.add_argument("--remediation-gate", default="state/remediation/remediation_gate.json", help="Path to remediation gate JSON.")
    parser.add_argument("--schedule-dependency-gate", default="state/audit_schedule/final_execution_schedule_dependency_gate.json", help="Path to schedule dependency gate JSON.")
    parser.add_argument("--final-execution-discipline", default="state/final_execution/final_execution_discipline.json", help="Path to final execution discipline JSON.")
    parser.add_argument("--runner-index", default="state/audit_runner/runner_index.json", help="Path to runner index JSON.")
    parser.add_argument("--report-gate", default=None, help="Optional path to report gate JSON.")
    parser.add_argument("--export-gate", default=None, help="Optional path to export gate JSON.")
    parser.add_argument("--release-surface", default="state/release_surface/release_surface.json", help="Path to release surface JSON.")
    parser.add_argument("--finalize-release-artifact", default="state/finalize/finalize_release_artifact.json", help="Path to finalize release artifact JSON.")
    parser.add_argument("--finalize-decision", default="state/finalize/finalize_decision.json", help="Path to finalize decision JSON.")
    parser.add_argument("--immutable-release-package", default="state/finalize/immutable_release_package.json", help="Path to immutable release package JSON.")
    parser.add_argument("--finalization-receipt", default="state/finalize/finalization_receipt.json", help="Path to finalization receipt JSON.")
    parser.add_argument("--production-readiness", default="state/control_plane/production_readiness.json", help="Path to production readiness JSON.")
    parser.add_argument("--run-result", default="state/e2e/run_result.json", help="Path to e2e run result JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    paths = TenetE2EPaths(
        raw_reason_output=args.raw_reason_output,
        canonical_reason_artifacts=args.canonical_reason_artifacts,
        execution_outcomes=args.execution_outcomes,
        jobs=args.jobs,
        execution_state=args.execution_state,
        execution_records=args.execution_records,
        execution_index=args.execution_index,
        remediation_state=args.remediation_state,
        remediation_items=args.remediation_items,
        remediation_index=args.remediation_index,
        remediation_gate=args.remediation_gate,
        schedule_dependency_gate=args.schedule_dependency_gate,
        final_execution_discipline=args.final_execution_discipline,
        runner_index=args.runner_index,
        report_gate=args.report_gate,
        export_gate=args.export_gate,
        release_surface=args.release_surface,
        finalize_release_artifact=args.finalize_release_artifact,
        finalize_decision=args.finalize_decision,
        immutable_release_package=args.immutable_release_package,
        finalization_receipt=args.finalization_receipt,
        work_items=args.work_items,
        materialized_audits=args.materialized_audits,
        production_readiness=args.production_readiness,
    )

    result = run_tenet_e2e(paths)
    write_e2e_run_result(Path(args.run_result), result)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.overall_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
