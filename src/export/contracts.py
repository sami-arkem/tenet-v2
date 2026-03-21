from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class ExportInputs:
    audit_output_path: Path
    board_memo_path: Path
    regulator_memo_path: Path
    client_report_path: Path


@dataclass(frozen=True)
class ExportArtifacts:
    package_dir: Path
    board_docx: Path
    regulator_docx: Path
    client_docx: Path
    board_pdf: Path
    regulator_pdf: Path
    client_pdf: Path
    manifest_json: Path


def report_markdown_map(inputs: ExportInputs) -> Dict[str, Path]:
    return {
        "board_memo_markdown": inputs.board_memo_path,
        "regulator_memo_markdown": inputs.regulator_memo_path,
        "client_report_markdown": inputs.client_report_path,
    }
