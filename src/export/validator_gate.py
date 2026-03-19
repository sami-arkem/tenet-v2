from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.export.contracts import ExportInputs
from src.reporting.report_validator import assert_valid_report_outputs


class ExportGateError(RuntimeError):
    pass


def _read_text(path: Path) -> str:
    if not path.exists():
        raise ExportGateError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict:
    if not path.exists():
        raise ExportGateError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_validated_report_bundle(inputs: ExportInputs) -> tuple[Dict, Dict[str, str]]:
    audit_output = _read_json(inputs.audit_output_path)
    reports = {
        "board_memo_markdown": _read_text(inputs.board_memo_path),
        "regulator_memo_markdown": _read_text(inputs.regulator_memo_path),
        "client_report_markdown": _read_text(inputs.client_report_path),
    }

    try:
        assert_valid_report_outputs(audit_output, reports)
    except Exception as exc:
        raise ExportGateError(f"Export blocked by report validation failure: {exc}") from exc

    return audit_output, reports
