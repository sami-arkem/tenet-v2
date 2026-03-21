from __future__ import annotations

from pathlib import Path

from src.export.contracts import ExportArtifacts, ExportInputs
from src.export.docx_exporter import export_docx_set
from src.export.manifest import write_export_manifest
from src.export.pdf_exporter import export_pdf_set
from src.export.source_fingerprint import assert_source_fingerprints_unchanged, capture_source_fingerprints
from src.export.validator_gate import load_validated_report_bundle


def _audit_id_from_output(audit_output: dict) -> str:
    audit_id = audit_output.get("audit_meta", {}).get("audit_id", "")
    return audit_id or "unknown_audit"


def _cleanup_legacy_flat_exports(out_dir: Path) -> None:
    legacy_names = {
        "board_memo.docx",
        "regulator_memo.docx",
        "client_report.docx",
        "board_memo.pdf",
        "regulator_memo.pdf",
        "client_report.pdf",
    }
    for name in legacy_names:
        legacy_path = out_dir / name
        if legacy_path.exists() and legacy_path.is_file():
            legacy_path.unlink()


def export_validated_reports(inputs: ExportInputs, out_dir: Path = Path("logs/exports")) -> ExportArtifacts:
    source_paths = {
        "audit_output": inputs.audit_output_path,
        "board_memo_markdown": inputs.board_memo_path,
        "regulator_memo_markdown": inputs.regulator_memo_path,
        "client_report_markdown": inputs.client_report_path,
    }
    fingerprints = capture_source_fingerprints(source_paths)

    audit_output, reports = load_validated_report_bundle(inputs)

    assert_source_fingerprints_unchanged(source_paths, fingerprints)

    audit_id = _audit_id_from_output(audit_output)
    out_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_legacy_flat_exports(out_dir)
    target_dir = out_dir / audit_id
    target_dir.mkdir(parents=True, exist_ok=True)

    docx_paths = export_docx_set(
        reports["board_memo_markdown"],
        reports["regulator_memo_markdown"],
        reports["client_report_markdown"],
        target_dir,
        audit_id=audit_id,
    )
    pdf_paths = export_pdf_set(
        reports["board_memo_markdown"],
        reports["regulator_memo_markdown"],
        reports["client_report_markdown"],
        target_dir,
        audit_id=audit_id,
    )

    all_files = {
        **docx_paths,
        **pdf_paths,
    }

    manifest_path = write_export_manifest(audit_id, all_files, target_dir / f"{audit_id}_export_manifest.json")

    return ExportArtifacts(
        package_dir=target_dir,
        board_docx=docx_paths["board_docx"],
        regulator_docx=docx_paths["regulator_docx"],
        client_docx=docx_paths["client_docx"],
        board_pdf=pdf_paths["board_pdf"],
        regulator_pdf=pdf_paths["regulator_pdf"],
        client_pdf=pdf_paths["client_pdf"],
        manifest_json=manifest_path,
    )
