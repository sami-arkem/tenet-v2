from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_official_corpus_api_flow():
    seed_response = client.post("/v1/official-corpus/seed")
    assert seed_response.status_code == 200
    assert seed_response.json()["data"]["created_count"] == 5

    bootstrap_response = client.post("/v1/official-corpus/bootstrap")
    assert bootstrap_response.status_code == 200
    data = bootstrap_response.json()["data"]

    assert data["deterministic_authoritative"] is True
    assert data["official_source_count"] >= 5
    assert data["promotion"]["promoted_count"] >= 5
    assert data["ingestion"]["processed_count"] >= 5
    assert data["ingestion"]["failure_count"] == 0
