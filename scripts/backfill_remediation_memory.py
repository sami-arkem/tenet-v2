import json
from pathlib import Path

from src.memory.audit_memory import load_audit_memory_snapshot
from src.memory.remediation_memory import (
    build_remediation_snapshot_from_audit_memory,
    write_remediation_snapshot,
    load_remediation_snapshot,
    write_remediation_comparison,
)

snapshot_root = Path("data/memory/snapshots")
written = 0

for path in sorted(snapshot_root.rglob("*.json")):
    audit_memory = load_audit_memory_snapshot(path)
    remediation_snapshot = build_remediation_snapshot_from_audit_memory(audit_memory)
    out_path = write_remediation_snapshot(remediation_snapshot)
    written += 1
    print("remediation_snapshot:", out_path)

print("remediation_snapshot_count:", written)

remediation_root = Path("data/memory/remediation_snapshots")
comparison_count = 0

for entity_dir in sorted(p for p in remediation_root.iterdir() if p.is_dir()):
    snapshots = sorted(entity_dir.glob("*.json"))
    if len(snapshots) < 2:
        continue

    for prior_path, current_path in zip(snapshots[:-1], snapshots[1:]):
        prior = load_remediation_snapshot(prior_path)
        current = load_remediation_snapshot(current_path)
        out = write_remediation_comparison(prior, current)
        comparison_count += 1
        print("remediation_comparison:", out)

print("remediation_comparison_count:", comparison_count)
