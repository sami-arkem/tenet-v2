from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_dataset_ingestion_api_flow():
    seed_response = client.post("/v1/dataset-registry/seed-examples")
    assert seed_response.status_code == 200

    single_response = client.post("/v1/dataset-ingestion/datasets/dataset_uk_mlr_primary/ingest")
    assert single_response.status_code == 200
    single = single_response.json()["data"]
    assert single["dataset_id"] == "dataset_uk_mlr_primary"
    assert single["retrieval_ready"] is True

    status_response = client.get("/v1/dataset-ingestion/datasets/dataset_uk_mlr_primary/status")
    assert status_response.status_code == 200
    assert status_response.json()["data"]["dataset_id"] == "dataset_uk_mlr_primary"

    bulk_response = client.post("/v1/dataset-ingestion/ingest-all?only_active=true")
    assert bulk_response.status_code == 200
    bulk = bulk_response.json()["data"]
    assert bulk["processed_count"] >= 4
    assert bulk["failure_count"] == 0

    search_response = client.get(
        "/v1/dataset-ingestion/datasets/dataset_us_ofac_metadata/search?query=ofac%20sanctions&top_k=5"
    )
    assert search_response.status_code == 200
    data = search_response.json()["data"]
    assert data["dataset_id"] == "dataset_us_ofac_metadata"
    assert data["result_count"] >= 1
