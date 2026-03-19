from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_source_acquisition_api_flow():
    seed_response = client.post("/v1/source-acquisition/seed-examples")
    assert seed_response.status_code == 200
    assert len(seed_response.json()["data"]["created"]) >= 1

    registry_response = client.get("/v1/source-acquisition")
    assert registry_response.status_code == 200
    assert registry_response.json()["data"]["count"] >= 4

    summary_response = client.get("/v1/source-acquisition/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["data"]["deterministic_authoritative"] is True

    rebuild_response = client.post("/v1/source-acquisition/rebuild-index")
    assert rebuild_response.status_code == 200
    assert rebuild_response.json()["data"]["status"] == "compiled"

    eval_response = client.get("/v1/source-acquisition/sources/uk_fca_handbook_public/evaluate")
    assert eval_response.status_code == 200
    assert eval_response.json()["data"]["decision"] == "APPROVE"

    with patch("core.source_acquisition_service.robots_allowed", return_value=True):
        enhanced_response = client.get("/v1/source-acquisition/sources/uk_fca_handbook_public/evaluate-enhanced")
    assert enhanced_response.status_code == 200
    assert "provenance_checks" in enhanced_response.json()["data"]
