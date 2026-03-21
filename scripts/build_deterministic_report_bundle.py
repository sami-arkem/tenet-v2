import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reporting.build_report_pack import build_report_pack
from src.reporting.deterministic_report_writer import build_deterministic_report_outputs
from src.reporting.report_validator import assert_valid_report_outputs


def _path_from_env(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


audit_output_path = _path_from_env("TENET_AUDIT_OUTPUT_PATH", "logs/report_audit_output.json")
report_dir = _path_from_env("TENET_REPORT_OUTPUT_DIR", "logs")

audit_output = json.loads(audit_output_path.read_text(encoding="utf-8"))
report_dir.mkdir(parents=True, exist_ok=True)

reports = build_deterministic_report_outputs(audit_output)
assert_valid_report_outputs(audit_output, reports)

(report_dir / "report_audit_output.json").write_text(json.dumps(audit_output, indent=2), encoding="utf-8")
(report_dir / "report_pack.json").write_text(json.dumps(build_report_pack(audit_output), indent=2), encoding="utf-8")
(report_dir / "board_memo.md").write_text(reports["board_memo_markdown"], encoding="utf-8")
(report_dir / "regulator_memo.md").write_text(reports["regulator_memo_markdown"], encoding="utf-8")
(report_dir / "client_report.md").write_text(reports["client_report_markdown"], encoding="utf-8")

print("wrote", report_dir / "report_audit_output.json")
print("wrote", report_dir / "report_pack.json")
print("wrote", report_dir / "board_memo.md")
print("wrote", report_dir / "regulator_memo.md")
print("wrote", report_dir / "client_report.md")
print("report validation passed")
