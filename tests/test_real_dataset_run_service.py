from __future__ import annotations

import json
from pathlib import Path

from core.official_corpus_bootstrap_service import seed_official_sources
from core.real_dataset_run_service import (
    fetch_all_allowed_real_sources,
    fetch_real_source_to_dataset,
)


def test_fetch_real_source_to_dataset(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "sources"
    dataset_root = tmp_path / "datasets"
    run_root = tmp_path / "runs"

    from core import official_corpus_bootstrap_service as bootstrap_svc
    from core import real_dataset_run_service as svc

    monkeypatch.setattr(bootstrap_svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", source_root / "official")
    seed_official_sources(source_root / "official")
    monkeypatch.setattr(svc, "evaluate_source_for_ingestion_enhanced", lambda source_id, root=source_root: {
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
    monkeypatch.setattr(
        svc,
        "_fetch_public_url",
        lambda source_url, timeout_seconds=30: (
            b"OFAC sanctions official dataset snapshot",
            {
                "status_code": 200,
                "content_type": "text/plain",
                "content_length_header": "38",
                "final_url": source_url,
            },
        ),
    )

    payload = fetch_real_source_to_dataset(
        source_id="official_ofac_sanctions_list_service",
        source_root=source_root,
        dataset_root=dataset_root,
        run_root=run_root,
    )
    assert payload["source_id"] == "official_ofac_sanctions_list_service"
    assert payload["dataset_id"] == "dataset_official_ofac_sanctions_list_service"
    assert payload["deterministic_authoritative"] is True

    meta_path = Path(payload["paths"]["metadata_path"])
    manifest_path = Path(payload["paths"]["dataset_manifest_path"])
    ledger_path = Path(payload["paths"]["ledger_path"])
    latest_snapshot_path = Path(payload["paths"]["latest_snapshot_path"])
    assert meta_path.exists()
    assert manifest_path.exists()
    assert ledger_path.exists()
    assert latest_snapshot_path.exists()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    latest_snapshot = json.loads(latest_snapshot_path.read_text(encoding="utf-8"))
    assert meta["raw_size_bytes"] > 0
    assert manifest["loader"]["kind"] == "file_manifest"
    assert manifest["retrieval"]["ready"] is False
    assert ledger["entry_count"] == 1
    assert latest_snapshot["source_id"] == "official_ofac_sanctions_list_service"


def test_fetch_all_allowed_real_sources(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "sources"
    dataset_root = tmp_path / "datasets"
    run_root = tmp_path / "runs"

    from core import official_corpus_bootstrap_service as bootstrap_svc
    from core import real_dataset_run_service as svc

    monkeypatch.setattr(bootstrap_svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", source_root / "official")
    seed_official_sources(source_root / "official")
    monkeypatch.setattr(svc, "evaluate_source_for_ingestion_enhanced", lambda source_id, root=source_root: {
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
    monkeypatch.setattr(
        svc,
        "_fetch_public_url",
        lambda source_url, timeout_seconds=30: (
            f"downloaded from {source_url}".encode("utf-8"),
            {
                "status_code": 200,
                "content_type": "text/plain",
                "content_length_header": "10",
                "final_url": source_url,
            },
        ),
    )

    payload = fetch_all_allowed_real_sources(
        source_root=source_root,
        dataset_root=dataset_root,
        run_root=run_root,
    )
    assert payload["deterministic_authoritative"] is True
    assert payload["success_count"] == 5
    assert payload["failure_count"] == 0
    assert not any(row["source_id"] == "blocked_scraped_prohibited" for row in payload["successes"])
