import json
from pathlib import Path

from src.memory.audit_memory import (
    compare_audit_memory_snapshots,
    load_audit_memory_snapshot,
    write_audit_memory_comparison,
)


def _choose_snapshot_pair() -> tuple[Path, Path] | None:
    snapshot_root = Path("data/memory/snapshots")
    entity_dirs = sorted(path for path in snapshot_root.iterdir() if path.is_dir())

    # Prefer comparing two audits for the same entity when available.
    for entity_dir in entity_dirs:
        snapshots = sorted(entity_dir.glob("*.json"))
        if len(snapshots) >= 2:
            return snapshots[-2], snapshots[-1]

    # Fall back to any two snapshots so the comparison path stays exercised.
    all_snapshots = sorted(snapshot_root.rglob("*.json"))
    if len(all_snapshots) >= 2:
        return all_snapshots[0], all_snapshots[1]
    return None


pair = _choose_snapshot_pair()
if pair is None:
    print("comparison skipped: not enough memory snapshots found")
else:
    prior_path, current_path = pair
    prior = load_audit_memory_snapshot(prior_path)
    current = load_audit_memory_snapshot(current_path)
    out = write_audit_memory_comparison(prior, current)
    print("comparison_source_prior:", prior_path)
    print("comparison_source_current:", current_path)
    print("comparison:", out)
    print(json.dumps(compare_audit_memory_snapshots(prior, current), indent=2))
