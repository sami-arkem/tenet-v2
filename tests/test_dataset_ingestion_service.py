from __future__ import annotations

from pathlib import Path

from core.dataset_ingestion_service import (
    get_dataset_ingestion_status,
    ingest_all_datasets,
    ingest_dataset,
    search_dataset_index,
)
from core.dataset_registry_service import seed_example_datasets


def test_ingest_single_file_manifest_dataset(tmp_path: Path):
    seed_example_datasets(tmp_path)

    payload = ingest_dataset(
        dataset_id="dataset_global_vendor_risk_standard",
        root=tmp_path,
    )
    assert payload["dataset_id"] == "dataset_global_vendor_risk_standard"
    assert payload["retrieval_ready"] is True
    assert payload["chunk_count"] >= 1
    assert Path(payload["normalized_text_path"]).exists()
    assert Path(payload["index_path"]).exists()

    loaded = get_dataset_ingestion_status(
        dataset_id="dataset_global_vendor_risk_standard",
        root=tmp_path,
    )
    assert loaded["dataset_id"] == "dataset_global_vendor_risk_standard"
    assert loaded["retrieval_ready"] is True


def test_ingest_single_url_manifest_dataset(tmp_path: Path):
    seed_example_datasets(tmp_path)

    payload = ingest_dataset(
        dataset_id="dataset_uk_mlr_primary",
        root=tmp_path,
    )
    assert payload["dataset_id"] == "dataset_uk_mlr_primary"
    assert payload["retrieval_ready"] is True
    assert payload["chunk_count"] >= 1


def test_ingest_all_and_search(tmp_path: Path):
    seed_example_datasets(tmp_path)

    bulk = ingest_all_datasets(root=tmp_path, only_active=True)
    assert bulk["processed_count"] == 4
    assert bulk["failure_count"] == 0

    result = search_dataset_index(
        dataset_id="dataset_us_ofac_metadata",
        query="ofac sanctions metadata",
        root=tmp_path,
    )
    assert result["dataset_id"] == "dataset_us_ofac_metadata"
    assert result["result_count"] >= 1
