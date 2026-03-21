from __future__ import annotations

import json
from pathlib import Path

from core.official_corpus_bootstrap_service import seed_official_sources
from core.real_dataset_run_service import fetch_real_source_to_dataset
from core.regulatory_monitor_service import (
    get_monitor_run,
    get_regulatory_alert,
    list_monitor_runs,
    list_regulatory_alerts,
    run_regulatory_monitor,
)


def _seed_and_fetch(tmp_path: Path, monkeypatch) -> None:
    from core import official_corpus_bootstrap_service as bootstrap_svc

    monkeypatch.setattr(bootstrap_svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", tmp_path / "sources" / "official")
    seed_official_sources(tmp_path / "sources" / "official")

    from core import real_dataset_run_service as run_svc

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

    fetch_real_source_to_dataset(
        source_id="official_ofac_sanctions_list_service",
        source_root=tmp_path / "sources",
        dataset_root=tmp_path / "datasets",
        run_root=tmp_path / "runs",
    )


def test_regulatory_monitor_creates_alert_on_change(tmp_path: Path, monkeypatch):
    _seed_and_fetch(tmp_path, monkeypatch)

    first = run_regulatory_monitor(
        dataset_root=tmp_path / "datasets",
        run_root=tmp_path / "runs",
        alert_root=tmp_path / "alerts",
        state_root=tmp_path / "alerts" / "_state",
    )
    assert first["created_alert_count"] == 0

    meta_path = tmp_path / "runs" / "official_ofac_sanctions_list_service" / "fetch_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["raw_sha256"] = "changed-sha"
    meta["fetched_at"] = "2026-03-18T12:00:00+00:00"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    second = run_regulatory_monitor(
        dataset_root=tmp_path / "datasets",
        run_root=tmp_path / "runs",
        alert_root=tmp_path / "alerts",
        state_root=tmp_path / "alerts" / "_state",
    )
    assert second["created_alert_count"] == 1
    assert second["alerts"][0]["dataset_id"] == "dataset_official_ofac_sanctions_list_service"
    assert second["alerts"][0]["affects_controls"] is True

    alert_id = second["alerts"][0]["alert_id"]
    alert = get_regulatory_alert(alert_id, alert_root=tmp_path / "alerts")
    assert alert["alert_id"] == alert_id

    listed = list_regulatory_alerts(alert_root=tmp_path / "alerts")
    assert listed["count"] == 1

    run_detail = get_monitor_run(second["run_id"], alert_root=tmp_path / "alerts")
    assert run_detail["run_id"] == second["run_id"]

    run_list = list_monitor_runs(alert_root=tmp_path / "alerts")
    assert run_list["count"] == 2


def test_regulatory_monitor_no_change_no_alert(tmp_path: Path, monkeypatch):
    _seed_and_fetch(tmp_path, monkeypatch)

    first = run_regulatory_monitor(
        dataset_root=tmp_path / "datasets",
        run_root=tmp_path / "runs",
        alert_root=tmp_path / "alerts",
        state_root=tmp_path / "alerts" / "_state",
    )
    second = run_regulatory_monitor(
        dataset_root=tmp_path / "datasets",
        run_root=tmp_path / "runs",
        alert_root=tmp_path / "alerts",
        state_root=tmp_path / "alerts" / "_state",
    )

    assert first["created_alert_count"] == 0
    assert second["created_alert_count"] == 0
