from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_dataset_registry_api_flow():
    seed_response = client.post("/v1/dataset-registry/seed-examples")
    assert seed_response.status_code == 200
    assert len(seed_response.json()["data"]["created"]) >= 1

    registry_response = client.get("/v1/dataset-registry")
    assert registry_response.status_code == 200
    assert registry_response.json()["data"]["count"] >= 4

    coverage_response = client.get("/v1/dataset-registry/coverage")
    assert coverage_response.status_code == 200
    coverage = coverage_response.json()["data"]
    assert coverage["deterministic_authoritative"] is True
    assert coverage["registry_count"] >= 4

    filter_response = client.get("/v1/dataset-registry/filter?domain=aml")
    assert filter_response.status_code == 200
    assert filter_response.json()["data"]["count"] >= 2

    rr_filter_response = client.get("/v1/dataset-registry/filter?retrieval_ready_only=true")
    assert rr_filter_response.status_code == 200
    assert rr_filter_response.json()["data"]["count"] == 0
