from __future__ import annotations

import json
from pathlib import Path

from core.dataset_refresh_executor_service import (
    execute_dataset_refresh_run,
    get_dataset_refresh_run,
    list_dataset_refresh_runs,
)
from core.dataset_registry_service import seed_example_datasets


def test_execute_dataset_refresh_run(tmp_path: Path, monkeypatch):
    seed_example_datasets(tmp_path)

    stale = tmp_path / "eu_aml_guidance.json"
    payload = json.loads(stale.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2025-01-01T00:00:00+00:00"
    stale.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    from core import dataset_refresh_executor_service as svc

    monkeypatch.setattr(svc, "DEFAULT_DATASET_ROOT", tmp_path)
    monkeypatch.setattr(svc, "DEFAULT_REFRESH_RUN_ROOT", tmp_path / "_refresh_runs")
    monkeypatch.setattr(
        svc,
        "_execute_refresh_for_dataset",
        lambda dataset_row, dataset_root=tmp_path: {
            "dataset_id": dataset_row["dataset_id"],
            "source_id": "mock_source",
            "fetch_executed": True,
            "fetch_payload": {"ok": True},
            "ingestion_payload": {"ok": True},
            "refreshed_at": "2026-03-18T00:00:00+00:00",
            "deterministic_authoritative": True,
        },
    )

    result = execute_dataset_refresh_run(limit=10, refresh_run_root=tmp_path / "_refresh_runs")
    assert result["deterministic_authoritative"] is True
    assert result["success_count"] >= 1
    assert result["failure_count"] == 0

    loaded = get_dataset_refresh_run(
        run_id=result["run_id"],
        refresh_run_root=tmp_path / "_refresh_runs",
    )
    assert loaded["run_id"] == result["run_id"]

    listed = list_dataset_refresh_runs(refresh_run_root=tmp_path / "_refresh_runs")
    assert listed["count"] == 1


def test_execute_dataset_refresh_run_partial_failure(tmp_path: Path, monkeypatch):
    seed_example_datasets(tmp_path)

    stale = tmp_path / "eu_aml_guidance.json"
    payload = json.loads(stale.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2025-01-01T00:00:00+00:00"
    stale.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    from core import dataset_refresh_executor_service as svc

    monkeypatch.setattr(svc, "DEFAULT_DATASET_ROOT", tmp_path)
    monkeypatch.setattr(svc, "DEFAULT_REFRESH_RUN_ROOT", tmp_path / "_refresh_runs")
    calls = {"count": 0}

    def fake_execute(dataset_row, dataset_root=tmp_path):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("mock failure")
        return {
            "dataset_id": dataset_row["dataset_id"],
            "source_id": None,
            "fetch_executed": False,
            "fetch_payload": None,
            "ingestion_payload": {"ok": True},
            "refreshed_at": "2026-03-18T00:00:00+00:00",
            "deterministic_authoritative": True,
        }

    monkeypatch.setattr(svc, "_execute_refresh_for_dataset", fake_execute)

    result = execute_dataset_refresh_run(limit=10, refresh_run_root=tmp_path / "_refresh_runs")
    assert result["status"] == "PARTIAL_FAILURE"
    assert result["failure_count"] >= 1
