import json
from pathlib import Path

from src.reporting.deterministic_report_builder import build_deterministic_report_markdown_bundle
from src.reporting.report_validator import assert_valid_report_outputs
from src.export.contracts import ExportInputs
from src.export.export_bundle import export_validated_reports

case_id = "licensing_uae_vendor_readiness"
audit_output_path = Path(f"evals/gold_cases/{case_id}/initial_run_output.json")
if not audit_output_path.exists():
    raise SystemExit(f"Missing {audit_output_path}. Run deterministic outputs first.")

audit_output = json.loads(audit_output_path.read_text(encoding="utf-8"))
reports = build_deterministic_report_markdown_bundle(audit_output)
assert_valid_report_outputs(audit_output, reports)

out_root = Path("logs/future_pack_smoke")
out_root.mkdir(parents=True, exist_ok=True)

audit_json = out_root / f"{case_id}_report_audit_output.json"
board_md = out_root / f"{case_id}_board_memo.md"
regulator_md = out_root / f"{case_id}_regulator_memo.md"
client_md = out_root / f"{case_id}_client_report.md"

audit_json.write_text(json.dumps(audit_output, indent=2), encoding="utf-8")
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
    out_dir=out_root / "exports",
)

print("exported", artifacts.board_docx)
print("exported", artifacts.regulator_docx)
print("exported", artifacts.client_docx)
print("exported", artifacts.board_pdf)
print("exported", artifacts.regulator_pdf)
print("exported", artifacts.client_pdf)
