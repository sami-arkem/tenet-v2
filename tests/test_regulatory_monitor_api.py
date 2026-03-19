from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_regulatory_monitor_api_flow(monkeypatch, tmp_path):
    from api.routers import official_corpus as official_corpus_router
    from api.routers import regulatory_monitor as monitor_router
    from api.routers import real_dataset_runs as real_dataset_runs_router
    from core import official_corpus_bootstrap_service as bootstrap_svc
    from core import real_dataset_run_service as run_svc

    monkeypatch.setattr(bootstrap_svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", tmp_path / "sources" / "official")
    monkeypatch.setattr(
        official_corpus_router,
        "seed_official_sources",
        lambda: __import__("core.official_corpus_bootstrap_service", fromlist=["seed_official_sources"]).seed_official_sources(
            tmp_path / "sources" / "official",
        ),
    )
    monkeypatch.setattr(
        run_svc,
        "evaluate_source_for_ingestion_enhanced",
        lambda source_id, root=None: {
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
        },
    )
    monkeypatch.setattr(
        run_svc,
        "_fetch_public_url",
        lambda source_url, timeout_seconds=30: (
            f"downloaded from {source_url}".encode("utf-8"),
            {
                "status_code": 200,
                "content_type": "text/plain",
                "content_length_header": "12",
                "final_url": source_url,
            },
        ),
    )

    monkeypatch.setattr(
        monitor_router,
        "run_regulatory_monitor",
        lambda: __import__("core.regulatory_monitor_service", fromlist=["run_regulatory_monitor"]).run_regulatory_monitor(
            dataset_root=tmp_path / "datasets",
            run_root=tmp_path / "runs",
            alert_root=tmp_path / "alerts",
            state_root=tmp_path / "alerts" / "_state",
        ),
    )
    monkeypatch.setattr(
        monitor_router,
        "list_regulatory_alerts",
        lambda: __import__("core.regulatory_monitor_service", fromlist=["list_regulatory_alerts"]).list_regulatory_alerts(
            alert_root=tmp_path / "alerts",
        ),
    )
    monkeypatch.setattr(
        monitor_router,
        "get_regulatory_alert",
        lambda alert_id: __import__("core.regulatory_monitor_service", fromlist=["get_regulatory_alert"]).get_regulatory_alert(
            alert_id,
            alert_root=tmp_path / "alerts",
        ),
    )
    monkeypatch.setattr(
        monitor_router,
        "list_monitor_runs",
        lambda: __import__("core.regulatory_monitor_service", fromlist=["list_monitor_runs"]).list_monitor_runs(
            alert_root=tmp_path / "alerts",
        ),
    )
    monkeypatch.setattr(
        monitor_router,
        "get_monitor_run",
        lambda run_id: __import__("core.regulatory_monitor_service", fromlist=["get_monitor_run"]).get_monitor_run(
            run_id,
            alert_root=tmp_path / "alerts",
        ),
    )
    monkeypatch.setattr(
        real_dataset_runs_router,
        "fetch_real_source_to_dataset",
        lambda source_id: __import__("core.real_dataset_run_service", fromlist=["fetch_real_source_to_dataset"]).fetch_real_source_to_dataset(
            source_id=source_id,
            source_root=tmp_path / "sources",
            dataset_root=tmp_path / "datasets",
            run_root=tmp_path / "runs",
        ),
    )

    seed_response = client.post("/v1/official-corpus/seed")
    assert seed_response.status_code == 200

    fetch_response = client.post("/v1/real-dataset-runs/sources/official_ofac_sanctions_list_service/fetch")
    assert fetch_response.status_code == 200

    first_run = client.post("/v1/regulatory-monitor/run")
    assert first_run.status_code == 200
    assert first_run.json()["data"]["created_alert_count"] == 0

    meta_path = tmp_path / "runs" / "official_ofac_sanctions_list_service" / "fetch_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["raw_sha256"] = "changed-sha"
    meta["fetched_at"] = "2026-03-18T12:00:00+00:00"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    second_run = client.post("/v1/regulatory-monitor/run")
    assert second_run.status_code == 200
    run_data = second_run.json()["data"]
    assert run_data["created_alert_count"] == 1
    alert_id = run_data["alerts"][0]["alert_id"]

    alerts_response = client.get("/v1/regulatory-monitor/alerts")
    assert alerts_response.status_code == 200
    assert alerts_response.json()["data"]["count"] >= 1

    alert_response = client.get(f"/v1/regulatory-monitor/alerts/{alert_id}")
    assert alert_response.status_code == 200
    assert alert_response.json()["data"]["alert_id"] == alert_id

    runs_response = client.get("/v1/regulatory-monitor/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["data"]["count"] >= 2
