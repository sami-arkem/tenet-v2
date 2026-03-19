import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports


def _path_from_env(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


inputs = ExportInputs(
    audit_output_path=_path_from_env("TENET_EXPORT_AUDIT_OUTPUT_PATH", "logs/report_audit_output.json"),
    board_memo_path=_path_from_env("TENET_EXPORT_BOARD_MEMO_PATH", "logs/board_memo.md"),
    regulator_memo_path=_path_from_env("TENET_EXPORT_REGULATOR_MEMO_PATH", "logs/regulator_memo.md"),
    client_report_path=_path_from_env("TENET_EXPORT_CLIENT_REPORT_PATH", "logs/client_report.md"),
)

artifacts = export_validated_reports(inputs, out_dir=_path_from_env("TENET_EXPORT_OUT_DIR", "logs/exports"))

print("package", artifacts.package_dir)
print("wrote", artifacts.board_docx)
print("wrote", artifacts.regulator_docx)
print("wrote", artifacts.client_docx)
print("wrote", artifacts.board_pdf)
print("wrote", artifacts.regulator_pdf)
print("wrote", artifacts.client_pdf)
print("wrote", artifacts.manifest_json)
