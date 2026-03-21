import json
from pathlib import Path

from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports
from src.export.validator_gate import ExportGateError, load_validated_report_bundle


def _write_inputs(tmp_path: Path, valid: bool) -> ExportInputs:
    audit_output = {
        "deployment_decision": {"status": "BLOCKED"},
        "entity_profile": {"legal_name": "Test Entity"},
        "findings": [{"title": "Transaction monitoring framework documented"}],
        "missing_controls": [{"control_id": "AML-003"}],
    }

    audit_path = tmp_path / "report_audit_output.json"
    board_path = tmp_path / "board_memo.md"
    regulator_path = tmp_path / "regulator_memo.md"
    client_path = tmp_path / "client_report.md"

    audit_path.write_text(json.dumps(audit_output), encoding="utf-8")
    board_path.write_text("## Board Memo\n\nTest Entity\n\nBLOCKED", encoding="utf-8")
    regulator_path.write_text("## Regulator Memo\n\nTest Entity\n\nBLOCKED\n\nAML-003", encoding="utf-8")

    if valid:
        client_text = "# Client Report\n\nTest Entity\n\nBLOCKED\n\nTransaction monitoring framework documented"
    else:
        client_text = "# Client Report\n\nTest Entity\n\nBLOCKED"

    client_path.write_text(client_text, encoding="utf-8")

    return ExportInputs(
        audit_output_path=audit_path,
        board_memo_path=board_path,
        regulator_memo_path=regulator_path,
        client_report_path=client_path,
    )


def test_load_validated_report_bundle_blocks_invalid(tmp_path: Path):
    inputs = _write_inputs(tmp_path, valid=False)
    try:
        load_validated_report_bundle(inputs)
    except ExportGateError as exc:
        assert "Export blocked by report validation failure" in str(exc)
    else:
        raise AssertionError("Expected ExportGateError")


def test_export_validated_reports_writes_files(tmp_path: Path):
    inputs = _write_inputs(tmp_path, valid=True)
    artifacts = export_validated_reports(inputs, out_dir=tmp_path / "exports")
    assert artifacts.package_dir == tmp_path / "exports" / "unknown_audit"
    assert artifacts.board_docx.exists()
    assert artifacts.regulator_docx.exists()
    assert artifacts.client_docx.exists()
    assert artifacts.board_pdf.exists()
    assert artifacts.regulator_pdf.exists()
    assert artifacts.client_pdf.exists()
    assert artifacts.manifest_json.exists()
