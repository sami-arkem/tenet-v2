from __future__ import annotations

import json
from pathlib import Path

from core.dataset_registry_service import validate_dataset_manifest
from core.source_acquisition_service import seed_example_sources
from core.source_dataset_promotion_service import (
    promote_all_allowed_sources,
    promote_source_to_dataset_manifest,
)


def test_promote_single_allowed_source(tmp_path: Path):
    source_root = tmp_path / "sources"
    dataset_root = tmp_path / "datasets"
    seed_example_sources(source_root)

    payload = promote_source_to_dataset_manifest(
        source_id="uk_fca_handbook_public",
        source_root=source_root,
        dataset_root=dataset_root,
    )
    assert payload["decision"] == "APPROVE"
    assert payload["dataset_manifest"]["dataset_id"] == "dataset_uk_fca_handbook_public"

    manifest_path = Path(payload["dataset_manifest_path"])
    assert manifest_path.exists()

    validated = validate_dataset_manifest(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        manifest_path,
    )
    assert validated.dataset_type == "law_text"
    assert validated.license_type == "PUBLIC"


def test_promote_blocked_source_fails(tmp_path: Path):
    source_root = tmp_path / "sources"
    dataset_root = tmp_path / "datasets"
    seed_example_sources(source_root)

    try:
        promote_source_to_dataset_manifest(
            source_id="blocked_scraped_prohibited",
            source_root=source_root,
            dataset_root=dataset_root,
        )
    except ValueError as exc:
        assert "not promotable" in str(exc)
    else:
        raise AssertionError("expected blocked source promotion to fail")


def test_promote_all_allowed_sources(tmp_path: Path):
    source_root = tmp_path / "sources"
    dataset_root = tmp_path / "datasets"
    seed_example_sources(source_root)

    payload = promote_all_allowed_sources(
        source_root=source_root,
        dataset_root=dataset_root,
    )
    assert payload["promoted_count"] == 3
    assert payload["skipped_count"] == 1
    assert payload["failure_count"] == 0
    assert payload["deterministic_authoritative"] is True
