import json
from pathlib import Path

raw_path = Path("logs/customer_pack_stability/raw_results.json")
rows = json.loads(raw_path.read_text(encoding="utf-8"))

summary = {
    "pack_count": len(rows),
    "successful_workflow_runs": sum(1 for r in rows if r["status"] == "success"),
    "failed_workflow_runs": sum(1 for r in rows if r["status"] != "success"),
    "successful_packs": [r["pack_name"] for r in rows if r["status"] == "success"],
    "failed_packs": [r["pack_name"] for r in rows if r["status"] != "success"],
}

Path("logs/customer_pack_stability/summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

print(json.dumps(summary, indent=2))
