import json
from pathlib import Path

from src.export.contracts import ExportInputs
from src.export.source_fingerprint import assert_source_fingerprints_unchanged, capture_source_fingerprints


def test_source_fingerprint_detects_change(tmp_path: Path):
    p = tmp_path / "file.md"
    p.write_text("one", encoding="utf-8")

    paths = {"file": p}
    before = capture_source_fingerprints(paths)

    p.write_text("two", encoding="utf-8")

    try:
        assert_source_fingerprints_unchanged(paths, before)
    except RuntimeError as exc:
        assert "source files changed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
