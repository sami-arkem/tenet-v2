from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.end_to_end_pipeline_reconciler import (
    build_pipeline_reconciliation_result,
    load_artifact,
    load_execution_records,
    load_jobs,
    load_materialized_audit_records,
    load_work_items,
    write_jobs,
    write_materialized_audits,
    write_production_readiness,
    write_work_items,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile end-to-end pipeline state from execution results and finalization receipt."
    )
    parser.add_argument(
        "--work-items",
        default="state/audit_workflow/work_items.jsonl",
        help="Path to work items JSONL.",
    )
    parser.add_argument(
        "--jobs",
        default="state/audit_runner/jobs.jsonl",
        help="Path to jobs JSONL.",
    )
    parser.add_argument(
        "--materialized-audits",
        default="state/audit_schedule/materialized_audit_records.jsonl",
        help="Path to materialized audit records JSONL.",
    )
    parser.add_argument(
        "--execution-records",
        default="state/audit_execution/execution_records.jsonl",
        help="Path to execution records JSONL.",
    )
    parser.add_argument(
        "--finalization-receipt",
        default="state/finalize/finalization_receipt.json",
        help="Path to finalization receipt JSON.",
    )
    parser.add_argument(
        "--readiness-output",
        default="state/control_plane/production_readiness.json",
        help="Path to production readiness JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    work_items = load_work_items(Path(args.work_items))
    jobs = load_jobs(Path(args.jobs))
    materialized_audits = load_materialized_audit_records(Path(args.materialized_audits))
    execution_records = load_execution_records(Path(args.execution_records))
    finalization_receipt = load_artifact(Path(args.finalization_receipt))

    result = build_pipeline_reconciliation_result(
        work_items=work_items,
        jobs=jobs,
        materialized_audit_records=materialized_audits,
        execution_records=execution_records,
        finalization_receipt=finalization_receipt,
    )

    write_work_items(Path(args.work_items), result.reconciled_work_items)
    write_jobs(Path(args.jobs), result.reconciled_jobs)
    write_materialized_audits(Path(args.materialized_audits), result.reconciled_materialized_audits)
    write_production_readiness(Path(args.readiness_output), result.production_readiness)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.production_readiness.readiness_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
