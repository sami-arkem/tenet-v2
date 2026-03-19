import json
from pathlib import Path

from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports


def _write_inputs(tmp_path: Path) -> ExportInputs:
    audit_output = {
        "audit_meta": {"audit_id": "audit-123"},
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
    client_path.write_text("# Client Report\n\nTest Entity\n\nBLOCKED\n\nTransaction monitoring framework documented", encoding="utf-8")

    return ExportInputs(
        audit_output_path=audit_path,
        board_memo_path=board_path,
        regulator_memo_path=regulator_path,
        client_report_path=client_path,
    )


def test_export_writes_manifest_and_audit_id_filenames(tmp_path: Path):
    inputs = _write_inputs(tmp_path)
    artifacts = export_validated_reports(inputs, out_dir=tmp_path / "exports")
    export_dir = tmp_path / "exports" / "audit-123"
    manifest = export_dir / "audit-123_export_manifest.json"

    assert artifacts.package_dir == export_dir
    assert artifacts.board_docx.name == "audit-123_board_memo.docx"
    assert artifacts.regulator_pdf.name == "audit-123_regulator_memo.pdf"
    assert artifacts.manifest_json == manifest
    assert manifest.exists()
