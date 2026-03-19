from __future__ import annotations

import json
from pathlib import Path

from core.dataset_freshness_service import (
    build_dataset_freshness_registry,
    build_refresh_plan,
    get_dataset_freshness_status,
)
from core.dataset_registry_service import seed_example_datasets


def test_build_dataset_freshness_registry(tmp_path: Path):
    seed_example_datasets(tmp_path)

    fresh = tmp_path / "uk_aml_mlr.json"
    payload = json.loads(fresh.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2026-03-17T00:00:00+00:00"
    fresh.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    stale = tmp_path / "eu_aml_guidance.json"
    payload = json.loads(stale.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2026-01-01T00:00:00+00:00"
    stale.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    registry = build_dataset_freshness_registry(
        dataset_root=tmp_path,
        freshness_root=tmp_path / "_freshness",
    )
    assert registry["deterministic_authoritative"] is True
    assert registry["dataset_count"] == 4
    assert registry["fresh"] >= 1
    assert registry["stale"] + registry["expired"] + registry["unknown"] >= 1

    item = get_dataset_freshness_status(
        dataset_id="dataset_uk_mlr_primary",
        freshness_root=tmp_path / "_freshness",
    )
    assert item["dataset_id"] == "dataset_uk_mlr_primary"
    assert item["freshness_state"] == "FRESH"


def test_build_refresh_plan(tmp_path: Path):
    seed_example_datasets(tmp_path)

    stale = tmp_path / "eu_aml_guidance.json"
    payload = json.loads(stale.read_text(encoding="utf-8"))
    payload["retrieval"]["ready"] = True
    payload["retrieval"]["last_ingested_at"] = "2025-01-01T00:00:00+00:00"
    stale.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    plan = build_refresh_plan(
        dataset_root=tmp_path,
        freshness_root=tmp_path / "_freshness",
        limit=10,
    )
    assert plan["deterministic_authoritative"] is True
    assert plan["candidate_count"] >= 1
    assert plan["scheduled_count"] >= 1
    assert any(row["dataset_id"] == "dataset_eu_amld_guidance" for row in plan["items"])
