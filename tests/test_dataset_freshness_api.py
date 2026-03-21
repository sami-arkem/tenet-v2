from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_dataset_freshness_api_flow():
    seed_response = client.post("/v1/dataset-registry/seed-examples")
    assert seed_response.status_code == 200

    rebuild_response = client.post("/v1/dataset-freshness/rebuild")
    assert rebuild_response.status_code == 200
    rebuilt = rebuild_response.json()["data"]
    assert rebuilt["deterministic_authoritative"] is True
    assert rebuilt["dataset_count"] >= 4

    item_response = client.get("/v1/dataset-freshness/datasets/dataset_uk_mlr_primary")
    assert item_response.status_code == 200
    assert item_response.json()["data"]["dataset_id"] == "dataset_uk_mlr_primary"

    plan_response = client.get("/v1/dataset-freshness/refresh-plan?limit=10")
    assert plan_response.status_code == 200
    assert plan_response.json()["data"]["deterministic_authoritative"] is True
