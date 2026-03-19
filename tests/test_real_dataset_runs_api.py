from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_real_dataset_runs_api_flow(monkeypatch, tmp_path):
    from core import official_corpus_bootstrap_service as bootstrap_svc
    from core import real_dataset_run_service as run_svc

    monkeypatch.setattr(bootstrap_svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", tmp_path / "sources" / "official")
    monkeypatch.setattr(run_svc, "evaluate_source_for_ingestion_enhanced", lambda source_id, root=None: {
        "source_id": source_id,
        "decision": "APPROVE",
        "reasons": ["approved_for_ingestion"],
        "source": {},
        "provenance_checks": {
            "robots_ok": True,
            "freshness_ok": True,
            "license_ok": True,
            "approved": True,
            "retrieval_allowed": True,
        },
    })

    seed_response = client.post("/v1/official-corpus/seed")
    assert seed_response.status_code == 200
    assert seed_response.json()["data"]["created_count"] == 5

    monkeypatch.setattr(
        run_svc,
        "_fetch_public_url",
        lambda source_url, timeout_seconds=30: (
            f"live official content from {source_url}".encode("utf-8"),
            {
                "status_code": 200,
                "content_type": "text/plain",
                "content_length_header": "20",
                "final_url": source_url,
            },
        ),
    )

    one_response = client.post("/v1/real-dataset-runs/sources/official_ofac_sanctions_list_service/fetch")
    assert one_response.status_code == 200
    one = one_response.json()["data"]
    assert one["dataset_id"] == "dataset_official_ofac_sanctions_list_service"
    assert one["deterministic_authoritative"] is True

    bulk_response = client.post("/v1/real-dataset-runs/fetch-all")
    assert bulk_response.status_code == 200
    bulk = bulk_response.json()["data"]
    assert bulk["success_count"] >= 5
    assert bulk["failure_count"] == 0
