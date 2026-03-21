from __future__ import annotations

from pathlib import Path

from core.dataset_registry_service import load_dataset_registry
from core.official_corpus_bootstrap_service import (
    bootstrap_official_corpus,
    seed_official_sources,
)
from core.source_acquisition_service import load_source_registry


def test_seed_official_sources(tmp_path: Path):
    root = tmp_path / "sources" / "official"
    payload = seed_official_sources(root)

    assert payload["created_count"] == 5
    assert payload["deterministic_authoritative"] is True

    registry = load_source_registry(tmp_path / "sources")
    assert registry["count"] == 5
    assert any(item["source_id"] == "official_ofac_sanctions_list_service" for item in registry["items"])
    assert any(item["source_id"] == "official_fca_handbook" for item in registry["items"])


def test_bootstrap_official_corpus(tmp_path: Path, monkeypatch):
    from core import official_corpus_bootstrap_service as svc

    monkeypatch.setattr(svc, "DEFAULT_OFFICIAL_SOURCE_ROOT", tmp_path / "sources" / "official")

    payload = bootstrap_official_corpus(
        source_root=tmp_path / "sources",
        dataset_root=tmp_path / "datasets",
    )

    assert payload["deterministic_authoritative"] is True
    assert payload["official_source_count"] == 5
    assert payload["promotion"]["promoted_count"] == 5
    assert payload["promotion"]["failure_count"] == 0
    assert payload["ingestion"]["processed_count"] == 5
    assert payload["ingestion"]["failure_count"] == 0

    registry = load_dataset_registry(tmp_path / "datasets")
    assert registry["count"] == 5
    assert any(item["dataset_id"] == "dataset_official_ofac_sanctions_list_service" for item in registry["items"])
