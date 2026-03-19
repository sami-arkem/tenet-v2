from __future__ import annotations

from pathlib import Path

from core.dataset_registry_service import (
    build_dataset_coverage_summary,
    filter_datasets,
    load_dataset_registry,
    seed_example_datasets,
)


def test_seed_and_load_dataset_registry(tmp_path: Path):
    seed_example_datasets(tmp_path)
    registry = load_dataset_registry(tmp_path)

    assert registry["count"] == 4
    assert len(registry["errors"]) == 0
    assert any(item["dataset_id"] == "dataset_uk_mlr_primary" for item in registry["items"])
    assert any(item["dataset_id"] == "dataset_us_ofac_metadata" for item in registry["items"])


def test_build_dataset_coverage_summary(tmp_path: Path):
    seed_example_datasets(tmp_path)
    summary = build_dataset_coverage_summary(tmp_path)

    assert summary["deterministic_authoritative"] is True
    assert summary["registry_count"] == 4
    assert summary["retrieval_ready_count"] == 0
    assert summary["active_count"] == 4
    assert summary["coverage"]["by_domain"]["aml"] == 2
    assert summary["coverage"]["by_domain"]["sanctions"] == 1
    assert summary["validation"]["all_valid"] is True


def test_filter_datasets(tmp_path: Path):
    seed_example_datasets(tmp_path)

    aml = filter_datasets(domain="aml", root=tmp_path)
    assert aml["count"] == 2

    uk = filter_datasets(jurisdiction="uk", root=tmp_path)
    assert uk["count"] == 1
    assert uk["items"][0]["dataset_id"] == "dataset_uk_mlr_primary"

    retrieval_ready = filter_datasets(retrieval_ready_only=True, root=tmp_path)
    assert retrieval_ready["count"] == 0

    sanctions = filter_datasets(domain="sanctions", framework_id="OFAC", root=tmp_path)
    assert sanctions["count"] == 1
    assert sanctions["items"][0]["dataset_id"] == "dataset_us_ofac_metadata"
