from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.reason_output_bridge import (
    build_canonical_reason_artifact_bundle,
    load_reason_outputs,
    write_canonical_reason_artifact_bundle,
)
from core.reason_artifact_adapter import (
    build_canonical_execution_outcomes,
    write_canonical_execution_outcomes,
)
from core.deterministic_audit_execution_bridge import (
    build_execution_outputs,
    load_execution_state,
    load_existing_execution_records,
    load_jobs,
    save_execution_state,
    append_execution_records,
    write_execution_index,
)
from core.remediation_tracking_engine import (
    build_remediation_tracking_outputs,
    load_existing_remediation_items,
    load_remediation_state,
    save_remediation_state,
    append_remediation_items,
    write_remediation_gate,
    write_remediation_index,
)
from core.final_release_surface import (
    build_release_surface,
    load_artifact as load_release_input_artifact,
    write_release_surface,
)
from core.finalize_release_bridge import (
    build_finalize_release_artifact,
    write_finalize_release_artifact,
)
from core.finalize_hard_blocker import (
    build_finalize_decision,
    write_finalize_decision,
)
from core.immutable_release_package import (
    build_immutable_release_package,
    write_immutable_release_package,
)
from core.finalization_orchestrator import (
    build_finalization_receipt,
    write_finalization_receipt,
)
from core.end_to_end_pipeline_reconciler import (
    build_pipeline_reconciliation_result,
    load_execution_records as load_reconciler_execution_records,
    load_jobs as load_reconciler_jobs,
    load_materialized_audit_records,
    load_work_items,
    write_jobs as write_reconciled_jobs,
    write_materialized_audits,
    write_production_readiness,
    write_work_items,
)
from core.final_execution_discipline_runner import (
    build_final_execution_discipline,
    write_final_execution_discipline,
)


E2E_ORCHESTRATOR_SCHEMA_VERSION = "1.1"


@dataclass(frozen=True)
class TenetE2EPaths:
    raw_reason_output: str
    canonical_reason_artifacts: str
    execution_outcomes: str
    jobs: str
    execution_state: str
    execution_records: str
    execution_index: str
    remediation_state: str
    remediation_items: str
    remediation_index: str
    remediation_gate: str
    schedule_dependency_gate: str
    final_execution_discipline: str
    runner_index: str
    report_gate: Optional[str]
    export_gate: Optional[str]
    release_surface: str
    finalize_release_artifact: str
    finalize_decision: str
    immutable_release_package: str
    finalization_receipt: str
    work_items: str
    materialized_audits: str
    production_readiness: str


@dataclass(frozen=True)
class TenetE2ERunResult:
    schema_version: str
    overall_status: str
    overall_ready: bool
    canonical_reason_artifacts_path: str
    execution_outcomes_path: str
    execution_records_path: str
    execution_index_path: str
    remediation_gate_path: str
    final_execution_discipline_path: str
    release_surface_path: str
    finalize_release_artifact_path: str
    finalize_decision_path: str
    immutable_release_package_path: str
    finalization_receipt_path: str
    production_readiness_path: str
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _optional_artifact(path_value: Optional[str]) -> Optional[Dict[str, object]]:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return load_release_input_artifact(path)


def run_tenet_e2e(paths: TenetE2EPaths) -> TenetE2ERunResult:
    raw_reason_output_path = Path(paths.raw_reason_output)
    canonical_reason_artifacts_path = Path(paths.canonical_reason_artifacts)
    execution_outcomes_path = Path(paths.execution_outcomes)
    jobs_path = Path(paths.jobs)
    execution_state_path = Path(paths.execution_state)
    execution_records_path = Path(paths.execution_records)
    execution_index_path = Path(paths.execution_index)
    remediation_state_path = Path(paths.remediation_state)
    remediation_items_path = Path(paths.remediation_items)
    remediation_index_path = Path(paths.remediation_index)
    remediation_gate_path = Path(paths.remediation_gate)
    schedule_dependency_gate_path = Path(paths.schedule_dependency_gate)
    final_execution_discipline_path = Path(paths.final_execution_discipline)
    runner_index_path = Path(paths.runner_index)
    release_surface_path = Path(paths.release_surface)
    finalize_release_artifact_path = Path(paths.finalize_release_artifact)
    finalize_decision_path = Path(paths.finalize_decision)
    immutable_release_package_path = Path(paths.immutable_release_package)
    finalization_receipt_path = Path(paths.finalization_receipt)
    work_items_path = Path(paths.work_items)
    materialized_audits_path = Path(paths.materialized_audits)
    production_readiness_path = Path(paths.production_readiness)

    raw_reason_outputs = load_reason_outputs(raw_reason_output_path)
    canonical_reason_bundle = build_canonical_reason_artifact_bundle(raw_reason_outputs)
    write_canonical_reason_artifact_bundle(canonical_reason_artifacts_path, canonical_reason_bundle)

    canonical_execution_outcomes = build_canonical_execution_outcomes(
        [artifact.to_dict() for artifact in canonical_reason_bundle.canonical_reason_artifacts]
    )
    write_canonical_execution_outcomes(execution_outcomes_path, canonical_execution_outcomes)

    jobs = load_jobs(jobs_path)
    existing_execution_records = load_existing_execution_records(execution_records_path)
    execution_state = load_execution_state(execution_state_path)
    execution_result, next_execution_state = build_execution_outputs(
        jobs=jobs,
        execution_outcomes=canonical_execution_outcomes.job_outcomes,
        existing_execution_records=existing_execution_records,
        state=execution_state,
    )
    append_execution_records(records=execution_result.created_execution_records, path=execution_records_path)
    if execution_result.execution_index is None:
        raise ValueError("execution index was not produced")
    write_execution_index(execution_index_path, execution_result.execution_index)
    save_execution_state(execution_state_path, next_execution_state)

    all_execution_records = load_reconciler_execution_records(execution_records_path)

    existing_remediation_items = load_existing_remediation_items(remediation_items_path)
    remediation_state = load_remediation_state(remediation_state_path)
    remediation_result, next_remediation_state = build_remediation_tracking_outputs(
        canonical_reason_artifacts=[artifact.to_dict() for artifact in canonical_reason_bundle.canonical_reason_artifacts],
        execution_records=all_execution_records,
        existing_remediation_items=existing_remediation_items,
        state=remediation_state,
    )
    append_remediation_items(items=remediation_result.created_items, path=remediation_items_path)
    if remediation_result.remediation_index is None or remediation_result.remediation_gate is None:
        raise ValueError("remediation artifacts were not produced")
    write_remediation_index(remediation_index_path, remediation_result.remediation_index)
    write_remediation_gate(remediation_gate_path, remediation_result.remediation_gate)
    save_remediation_state(remediation_state_path, next_remediation_state)

    schedule_dependency_gate = load_release_input_artifact(schedule_dependency_gate_path)
    report_gate = _optional_artifact(paths.report_gate)
    export_gate = _optional_artifact(paths.export_gate)

    final_execution_discipline = build_final_execution_discipline(
        schedule_dependency_gate=schedule_dependency_gate,
        remediation_gate=remediation_result.remediation_gate.to_dict(),
        report_validation_gate=report_gate,
        export_gate=export_gate,
        proof_readiness_gate=None,
        release_gate=None,
    )
    write_final_execution_discipline(final_execution_discipline_path, final_execution_discipline)

    runner_index = load_release_input_artifact(runner_index_path)
    release_surface = build_release_surface(
        final_execution_discipline=final_execution_discipline.to_dict(),
        runner_index=runner_index,
        remediation_gate=remediation_result.remediation_gate.to_dict(),
        report_gate=report_gate,
        export_gate=export_gate,
    )
    write_release_surface(release_surface_path, release_surface)

    finalize_release_artifact = build_finalize_release_artifact(
        release_surface=release_surface.to_dict(),
        execution_index=execution_result.execution_index.to_dict(),
        execution_records=all_execution_records,
    )
    write_finalize_release_artifact(finalize_release_artifact_path, finalize_release_artifact)

    finalize_decision = build_finalize_decision(
        finalize_release_artifact=finalize_release_artifact.to_dict(),
        release_package_path=str(immutable_release_package_path),
    )
    write_finalize_decision(finalize_decision_path, finalize_decision)

    include_paths = [
        canonical_reason_artifacts_path,
        execution_outcomes_path,
        execution_index_path,
        remediation_index_path,
        remediation_gate_path,
        final_execution_discipline_path,
        release_surface_path,
        finalize_release_artifact_path,
        finalize_decision_path,
    ]
    if paths.report_gate:
        include_paths.append(Path(paths.report_gate))
    if paths.export_gate:
        include_paths.append(Path(paths.export_gate))

    immutable_release_package = build_immutable_release_package(
        finalize_decision=finalize_decision.to_dict(),
        files_to_include=include_paths,
        manifest_path=immutable_release_package_path,
    )
    write_immutable_release_package(immutable_release_package_path, immutable_release_package)

    finalization_receipt = build_finalization_receipt(
        finalize_decision=finalize_decision.to_dict(),
        immutable_release_package=immutable_release_package.to_dict(),
    )
    write_finalization_receipt(finalization_receipt_path, finalization_receipt)

    work_items = load_work_items(work_items_path)
    reconciler_jobs = load_reconciler_jobs(jobs_path)
    materialized_audits = load_materialized_audit_records(materialized_audits_path)

    reconciliation_result = build_pipeline_reconciliation_result(
        work_items=work_items,
        jobs=reconciler_jobs,
        materialized_audit_records=materialized_audits,
        execution_records=all_execution_records,
        finalization_receipt=finalization_receipt.to_dict(),
    )

    write_work_items(work_items_path, reconciliation_result.reconciled_work_items)
    write_reconciled_jobs(jobs_path, reconciliation_result.reconciled_jobs)
    write_materialized_audits(materialized_audits_path, reconciliation_result.reconciled_materialized_audits)
    write_production_readiness(production_readiness_path, reconciliation_result.production_readiness)

    overall_ready = reconciliation_result.production_readiness.readiness_ready
    overall_status = reconciliation_result.production_readiness.readiness_status
    blocking_reasons = reconciliation_result.production_readiness.blocking_reasons

    return TenetE2ERunResult(
        schema_version=E2E_ORCHESTRATOR_SCHEMA_VERSION,
        overall_status=overall_status,
        overall_ready=overall_ready,
        canonical_reason_artifacts_path=str(canonical_reason_artifacts_path),
        execution_outcomes_path=str(execution_outcomes_path),
        execution_records_path=str(execution_records_path),
        execution_index_path=str(execution_index_path),
        remediation_gate_path=str(remediation_gate_path),
        final_execution_discipline_path=str(final_execution_discipline_path),
        release_surface_path=str(release_surface_path),
        finalize_release_artifact_path=str(finalize_release_artifact_path),
        finalize_decision_path=str(finalize_decision_path),
        immutable_release_package_path=str(immutable_release_package_path),
        finalization_receipt_path=str(finalization_receipt_path),
        production_readiness_path=str(production_readiness_path),
        blocking_reasons=blocking_reasons,
    )


def write_e2e_run_result(path: Path, result: TenetE2ERunResult) -> None:
    _write_json(path, result.to_dict())
