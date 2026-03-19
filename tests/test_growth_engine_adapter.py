from __future__ import annotations

from pathlib import Path

from core.source_acquisition_service import validate_source_manifest
from incubator.growth_engine.source_gate_adapter import (
    GrowthSourceCandidate,
    write_candidate_manifest,
)


def test_growth_source_candidate_writes_canonical_source_manifest(tmp_path: Path):
    candidate = GrowthSourceCandidate(
        source_id="growth_candidate_public_001",
        title="Public Regulatory Feed Candidate",
        domain="aml",
        jurisdictions=["uk"],
        countries=["GB"],
        source_class="PUBLIC_OFFICIAL",
        acquisition_method="PUBLIC_DOWNLOAD",
        license_status="PUBLIC",
        owner="growth_engine",
        source_url="https://www.fca.org.uk/handbook",
        approved=True,
        retrieval_allowed=True,
        metadata={"origin": "incubator"},
    )

    path = tmp_path / "candidate.json"
    manifest = write_candidate_manifest(candidate, path)
    record = validate_source_manifest(manifest, path)

    assert record.source_id == "growth_candidate_public_001"
    assert record.source_class == "PUBLIC_OFFICIAL"
    assert record.license_status == "PUBLIC"
