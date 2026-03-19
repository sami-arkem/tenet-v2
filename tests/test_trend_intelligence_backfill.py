from pathlib import Path


def test_trend_backfill_has_memory_inputs():
    audit_root = Path("data/memory/snapshots")
    assert audit_root.exists()
    assert any(audit_root.rglob("*.json"))
