from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_source_dataset_promotion_api_flow():
    seed_response = client.post("/v1/source-acquisition/seed-examples")
    assert seed_response.status_code == 200

    promote_one = client.post(
        "/v1/source-dataset-promotion/sources/uk_fca_handbook_public/promote",
        json={},
    )
    assert promote_one.status_code == 200
    one = promote_one.json()["data"]
    assert one["decision"] == "APPROVE"
    assert one["dataset_manifest"]["dataset_id"] == "dataset_uk_fca_handbook_public"

    promote_all = client.post("/v1/source-dataset-promotion/promote-all")
    assert promote_all.status_code == 200
    all_data = promote_all.json()["data"]
    assert all_data["promoted_count"] >= 3
    assert all_data["skipped_count"] >= 1
    assert all_data["deterministic_authoritative"] is True
