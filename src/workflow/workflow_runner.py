from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.core.io_utils import atomic_write_json, atomic_write_text
from src.reasoning.reason import reason
from src.reporting.deterministic_report_builder import build_deterministic_report_markdown_bundle
from src.reporting.report_validator import assert_valid_report_outputs
from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports
from src.memory.audit_memory import build_audit_memory_snapshot, write_audit_memory_snapshot
from src.memory.remediation_memory import build_remediation_snapshot_from_audit_memory, write_remediation_snapshot
from src.memory.trend_intelligence import write_entity_trend_summary
from src.workflow.evidence_pack_loader import load_evidence_pack


def _read_workflow_runtime() -> Dict[str, Any]:
    path = Path("data/config/workflow_runtime_v1.json")
    if not path.exists():
        raise FileNotFoundError(f"Missing workflow runtime config: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_customer_evidence_pack(pack_dir: str | Path) -> Dict[str, Any]:
    runtime = _read_workflow_runtime()
    pack = load_evidence_pack(pack_dir)

    audit_context = pack["audit_context"]
    audit_output = reason(
        audit_context=audit_context,
        reasoner=None,
        runtime_config={
            "enable_model_reasoning": runtime["enable_model_reasoning"],
            "model_overlay_sections": runtime["model_overlay_sections"],
            "fallback_to_deterministic_on_model_error": runtime["fallback_to_deterministic_on_model_error"],
            "require_retrieved_chunks_for_model_reasoning": runtime["require_retrieved_chunks_for_model_reasoning"],
        },
    )

    pack_path = Path(pack["pack_dir"])
    run_dir = pack_path / "tenet_run"
    run_dir.mkdir(parents=True, exist_ok=True)

    audit_output_path = run_dir / "audit_output.json"
    atomic_write_json(audit_output_path, audit_output)

    result: Dict[str, Any] = {
        "pack_dir": str(pack_path),
        "run_dir": str(run_dir),
        "audit_output_path": str(audit_output_path),
    }

    reports = None
    if runtime.get("enable_report_generation", False):
        reports = build_deterministic_report_markdown_bundle(audit_output)
        assert_valid_report_outputs(audit_output, reports)

        board_md = run_dir / "board_memo.md"
        regulator_md = run_dir / "regulator_memo.md"
        client_md = run_dir / "client_report.md"

        atomic_write_text(board_md, reports["board_memo_markdown"])
        atomic_write_text(regulator_md, reports["regulator_memo_markdown"])
        atomic_write_text(client_md, reports["client_report_markdown"])

        result.update({
            "board_memo_path": str(board_md),
            "regulator_memo_path": str(regulator_md),
            "client_report_path": str(client_md),
        })

        if runtime.get("enable_export", False):
            artifacts = export_validated_reports(
                ExportInputs(
                    audit_output_path=audit_output_path,
                    board_memo_path=board_md,
                    regulator_memo_path=regulator_md,
                    client_report_path=client_md,
                ),
                out_dir=run_dir / "exports",
            )
            result.update({
                "board_docx_path": str(artifacts.board_docx),
                "regulator_docx_path": str(artifacts.regulator_docx),
                "client_docx_path": str(artifacts.client_docx),
                "board_pdf_path": str(artifacts.board_pdf),
                "regulator_pdf_path": str(artifacts.regulator_pdf),
                "client_pdf_path": str(artifacts.client_pdf),
            })

    audit_memory_path = None
    remediation_memory_path = None
    trend_path = None

    if runtime.get("enable_audit_memory", False):
        audit_memory_path = write_audit_memory_snapshot(audit_output)
        result["audit_memory_path"] = str(audit_memory_path)

    if runtime.get("enable_remediation_memory", False):
        audit_memory_snapshot = build_audit_memory_snapshot(audit_output)
        remediation_snapshot = build_remediation_snapshot_from_audit_memory(audit_memory_snapshot)
        remediation_memory_path = write_remediation_snapshot(remediation_snapshot)
        result["remediation_memory_path"] = str(remediation_memory_path)

    if runtime.get("enable_trend_refresh", False):
        entity_name = (
            audit_output.get("entity_profile", {}).get("legal_name", "")
            or audit_output.get("entity_profile", {}).get("entity_name", "")
            or audit_context.get("entity_name", "")
        )
        trend = write_entity_trend_summary(entity_name)
        if trend is not None:
            trend_path = trend
            result["trend_summary_path"] = str(trend_path)

    summary_path = run_dir / "workflow_result.json"
    result["workflow_result_path"] = str(summary_path)
    atomic_write_json(summary_path, result)

    return result
