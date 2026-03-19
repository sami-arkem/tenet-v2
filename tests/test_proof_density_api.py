from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_proof_density_seed_and_summary_flow():
    seed_response = client.post("/v1/proof-density/seed-examples")
    assert seed_response.status_code == 200

    gold_response = client.get("/v1/proof-density/gold-cases")
    assert gold_response.status_code == 200
    assert gold_response.json()["data"]["count"] >= 1

    pack_response = client.get("/v1/proof-density/customer-packs")
    assert pack_response.status_code == 200
    assert pack_response.json()["data"]["count"] >= 1

    summary_response = client.get("/v1/proof-density/summary")
    assert summary_response.status_code == 200
    data = summary_response.json()["data"]
    assert data["deterministic_authoritative"] is True
    assert data["current"]["gold_cases"] >= 1
    assert data["current"]["customer_packs"] >= 1
    assert "gold_cases" in data["progress_percent"]
    assert "customer_packs" in data["progress_percent"]
