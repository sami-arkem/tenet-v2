import json
from pathlib import Path

def test_customer_pack_stability_summary_if_present():
    path = Path("logs/customer_pack_stability/summary.json")
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "pack_count" in data
    assert "successful_workflow_runs" in data
    assert "failed_workflow_runs" in data
