import json
from pathlib import Path

from src.memory.audit_memory import write_audit_memory_snapshot

gold_root = Path("evals/gold_cases")
count = 0

for case_dir in sorted(p for p in gold_root.iterdir() if p.is_dir()):
    output_path = case_dir / "initial_run_output.json"
    if not output_path.exists():
        continue

    audit_output = json.loads(output_path.read_text(encoding="utf-8"))
    out_path = write_audit_memory_snapshot(audit_output)
    count += 1
    print("snapshot:", out_path)

print("snapshot_count:", count)
