import json
from pathlib import Path

from scripts.final_execution_discipline import _base_env, _json_from_step_stdout


def test_final_execution_helpers():
    env = _base_env()
    assert env["PYTHONPATH"] == "."

    steps = [
        {
            "name": "readiness_check",
            "passed": True,
            "stdout": '{"overall_readiness": true}',
        }
    ]
    parsed = _json_from_step_stdout(steps, "readiness_check")
    assert parsed["overall_readiness"] is True


def test_final_execution_summary_shape_if_present():
    path = Path("logs/final_execution_summary.json")
    if not path.exists():
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "all_steps_passed" in data
    assert "steps" in data
    assert "eval" in data
    assert "customer_pack_stability" in data
    assert "boardroom_historical_reporting" in data
    if "timed_out" in data["steps"][0]:
        assert "duration_seconds" in data["steps"][0]
