from pathlib import Path


def test_audit_memory_snapshots_exist_for_remediation_backfill():
    snapshot_root = Path("data/memory/snapshots")
    count = sum(1 for _ in snapshot_root.rglob("*.json"))
    assert count >= 8
