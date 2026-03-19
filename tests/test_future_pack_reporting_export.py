import json
from pathlib import Path

from src.reporting.deterministic_report_builder import build_deterministic_report_markdown_bundle
from src.reporting.report_validator import validate_report_outputs
from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports


def test_future_pack_deterministic_reports_validate_and_export(tmp_path: Path):
    case_path = Path("evals/gold_cases/licensing_uae_vendor_readiness/initial_run_output.json")
    audit_output = json.loads(case_path.read_text(encoding="utf-8"))

    reports = build_deterministic_report_markdown_bundle(audit_output)
    failures = validate_report_outputs(audit_output, reports)
    assert failures == []

    audit_json = tmp_path / "audit_output.json"
    board_md = tmp_path / "board_memo.md"
    regulator_md = tmp_path / "regulator_memo.md"
    client_md = tmp_path / "client_report.md"

    audit_json.write_text(json.dumps(audit_output), encoding="utf-8")
    board_md.write_text(reports["board_memo_markdown"], encoding="utf-8")
    regulator_md.write_text(reports["regulator_memo_markdown"], encoding="utf-8")
    client_md.write_text(reports["client_report_markdown"], encoding="utf-8")

    artifacts = export_validated_reports(
        ExportInputs(
            audit_output_path=audit_json,
            board_memo_path=board_md,
            regulator_memo_path=regulator_md,
            client_report_path=client_md,
        ),
        out_dir=tmp_path / "exports",
    )

    assert artifacts.board_docx.exists()
    assert artifacts.regulator_pdf.exists()
    assert artifacts.client_pdf.exists()
