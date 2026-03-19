import json
from pathlib import Path

from src.reporting.report_validator import assert_valid_report_outputs

audit_path = Path("logs/report_audit_output.json")
board_path = Path("logs/board_memo.md")
regulator_path = Path("logs/regulator_memo.md")
client_path = Path("logs/client_report.md")

audit_output = json.loads(audit_path.read_text())
reports = {
    "board_memo_markdown": board_path.read_text(),
    "regulator_memo_markdown": regulator_path.read_text(),
    "client_report_markdown": client_path.read_text(),
}

assert_valid_report_outputs(audit_output, reports)
print("report validation passed")
