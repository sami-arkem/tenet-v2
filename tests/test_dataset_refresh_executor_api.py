from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_dataset_refresh_executor_api_flow(monkeypatch, tmp_path):
    from core import dataset_refresh_executor_service as svc

    seed_response = client.post("/v1/dataset-registry/seed-examples")
    assert seed_response.status_code == 200

    seeded_file = Path("fixtures/regulatory_datasets/eu_aml_guidance.json")
    payload = json.loads(seeded_file.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2025-01-01T00:00:00+00:00"
    seeded_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    monkeypatch.setattr(svc, "DEFAULT_REFRESH_RUN_ROOT", tmp_path / "_refresh_runs")
    monkeypatch.setattr(
        svc,
        "_execute_refresh_for_dataset",
        lambda dataset_row, dataset_root=svc.DEFAULT_DATASET_ROOT: {
            "dataset_id": dataset_row["dataset_id"],
            "source_id": "mock_source",
            "fetch_executed": True,
            "fetch_payload": {"ok": True},
            "ingestion_payload": {"ok": True},
            "refreshed_at": "2026-03-18T00:00:00+00:00",
            "deterministic_authoritative": True,
        },
    )

    run_response = client.post("/v1/dataset-refresh-executor/run?limit=10")
    assert run_response.status_code == 200
    run_data = run_response.json()["data"]
    assert run_data["deterministic_authoritative"] is True
    run_id = run_data["run_id"]

    get_response = client.get(f"/v1/dataset-refresh-executor/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["run_id"] == run_id

    list_response = client.get("/v1/dataset-refresh-executor/runs")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["count"] >= 1
