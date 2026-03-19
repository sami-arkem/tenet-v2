from pathlib import Path
import json


def test_gold_case_outputs_exist_for_memory_backfill():
    root = Path("evals/gold_cases")
    count = 0
    for case_dir in root.iterdir():
        if not case_dir.is_dir():
            continue
        if (case_dir / "initial_run_output.json").exists():
            count += 1
    assert count >= 8
