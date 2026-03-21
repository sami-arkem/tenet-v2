from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.source_acquisition_service import (
    SourceRecord,
    check_source_freshness,
    evaluate_source_for_ingestion,
    evaluate_source_for_ingestion_enhanced,
    get_source_by_id,
    rebuild_source_index,
    robots_allowed,
    seed_example_sources,
)


def _seed(tmp_path: Path) -> None:
    seed_example_sources(tmp_path)


def test_blocked_scraped_hard_block(tmp_path: Path):
    _seed(tmp_path)
    result = evaluate_source_for_ingestion(source_id="blocked_scraped_prohibited", root=tmp_path)
    assert result["decision"] == "BLOCK"
    assert any("SCRAPED_PROHIBITED" in reason or "blocked" in reason.lower() for reason in result["reasons"])


def test_public_official_approved(tmp_path: Path):
    _seed(tmp_path)
    result = evaluate_source_for_ingestion(source_id="uk_fca_handbook_public", root=tmp_path)
    assert result["decision"] == "APPROVE"


def test_robots_allowed_mocked():
    with patch("core.source_acquisition_service.RobotFileParser") as mock_rp:
        instance = MagicMock()
        instance.can_fetch.return_value = True
        mock_rp.return_value = instance
        assert robots_allowed("https://www.fca.org.uk/handbook") is True


def test_robots_blocked_mocked():
    with patch("core.source_acquisition_service.RobotFileParser") as mock_rp:
        instance = MagicMock()
        instance.can_fetch.return_value = False
        mock_rp.return_value = instance
        assert robots_allowed("https://blocked.example.com") is False


def test_robots_null_url():
    assert robots_allowed(None) is False
    assert robots_allowed("") is False


def test_freshness_stale_blocks():
    stale_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    record = SourceRecord(
        source_id="stale_test",
        title="Stale",
        domain="test",
        jurisdictions=["us"],
        countries=["US"],
        source_class="PUBLIC_OFFICIAL",
        acquisition_method="PUBLIC_DOWNLOAD",
        license_status="PUBLIC",
        owner="test",
        source_url="https://example.com",
        approved=True,
        retrieval_allowed=True,
        metadata={"freshness_check": "daily", "last_check": stale_time},
    )
    assert check_source_freshness(record, max_age_days=1) is False


def test_freshness_recent_passes():
    recent_time = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat().replace("+00:00", "Z")
    record = SourceRecord(
        source_id="fresh_test",
        title="Fresh",
        domain="test",
        jurisdictions=["us"],
        countries=["US"],
        source_class="PUBLIC_OFFICIAL",
        acquisition_method="PUBLIC_DOWNLOAD",
        license_status="PUBLIC",
        owner="test",
        source_url="https://example.com",
        approved=True,
        retrieval_allowed=True,
        metadata={"freshness_check": "daily", "last_check": recent_time},
    )
    assert check_source_freshness(record, max_age_days=1) is True


def test_enhanced_eval_adds_provenance(tmp_path: Path):
    _seed(tmp_path)
    with patch("core.source_acquisition_service.robots_allowed", return_value=True):
        result = evaluate_source_for_ingestion_enhanced(source_id="uk_fca_handbook_public", root=tmp_path)
    assert "provenance_checks" in result
    assert result["provenance_checks"]["robots_ok"] is True


def test_enhanced_eval_robots_block(tmp_path: Path):
    _seed(tmp_path)
    with patch("core.source_acquisition_service.robots_allowed", return_value=False):
        result = evaluate_source_for_ingestion_enhanced(source_id="uk_fca_handbook_public", root=tmp_path)
    assert result["decision"] == "BLOCK"
    assert "robots_txt_blocked" in result["reasons"]


def test_index_rebuild(tmp_path: Path):
    _seed(tmp_path)
    idx = rebuild_source_index(tmp_path)
    assert len(idx) >= 1
    for _, item in idx.items():
        assert "_checksum" in item


def test_indexed_lookup(tmp_path: Path):
    _seed(tmp_path)
    rebuild_source_index(tmp_path)
    record = get_source_by_id("uk_fca_handbook_public", tmp_path)
    assert record is not None
    assert record["source_class"] == "PUBLIC_OFFICIAL"


def test_indexed_lookup_miss(tmp_path: Path):
    _seed(tmp_path)
    rebuild_source_index(tmp_path)
    assert get_source_by_id("nonexistent_garbage_id", tmp_path) is None
