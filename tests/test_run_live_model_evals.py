from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path("scripts/run_live_model_evals.py")
    spec = importlib.util.spec_from_file_location("run_live_model_evals", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_is_recoverable_model_unavailable():
    module = load_module()
    exc = RuntimeError("Model call failed for gpt-4.1-mini: <urlopen error [Errno 8] nodename nor servname provided, or not known>")
    assert module._is_recoverable_model_unavailable(exc) is True


def test_load_cached_results_returns_empty_for_missing(tmp_path: Path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "SUMMARY_PATH", tmp_path / "missing.json")
    assert module._load_cached_results() == []


def test_load_cached_results_reads_list(tmp_path: Path, monkeypatch):
    module = load_module()
    summary = tmp_path / "live_model_eval_summary.json"
    summary.write_text(json.dumps([{"case_id": "x", "passed": True}]), encoding="utf-8")
    monkeypatch.setattr(module, "SUMMARY_PATH", summary)
    assert module._load_cached_results() == [{"case_id": "x", "passed": True}]
