from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_final_execution_discipline_import_bootstraps_repo_path():
    result = subprocess.run(
        [sys.executable, "-c", "import runpy; runpy.run_path('scripts/final_execution_discipline.py', run_name='not_main')"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
